# ==========================================================================================
# The explanation of this script is not completed. I have several places I don't understand.
# Longsheng Jiang April 28, 2020
# ==========================================================================================

try:
    import heapq
except ImportError:
    import ccm.legacy.heapq as heapq
import copy

from . import logger

class Trigger:
    """Dub the name as Trigger xxx"""
    def __init__(self,name=''):
        # Get the name xxx
        self.name=name
    def __str__(self):
        # Prefix the name with Trigger
        return '<Trigger "%s">'%self.name

class Event:
# This is wrapper to bind (1) a function, (2) the arguments and (3) keywords to the function,
# (4) the time to execute, and (5) the priority together into an object.
  generator=False
  def __init__(self,func,time,args=[],keys={},priority=0):
    # We first retrieve the function name of the function func.
    self.name=getattr(func,'func_name',None)
    # We try to obtain the code of the function.
    try:
       code=func.func_code
    # In the case the not code is avaiable,
    except AttributeError:
        # Try to retrieve the implicate code.
       try:
          code=func.__call__.im_func.func_code
        # In the case that still no code avaiable, we set the code to None.
       except:
          code=None
    # Let us now check if the contained code belongs to a generator.
    # If belonging to a generator,
    if code and code.co_flags&0x20==0x20:    # check for generator
        # we want let the generator to output one element a time. We do so by using the following statement.
        # For more information about python generator, please check this reference:
        # https://www.programiz.com/python-programming/generator
        func=func(*args,**keys).next
        # Make sure to clear the args and keys and to update the generator flag.
        args=[]
        keys={}
        self.generator=True
    # Here we finalize the attributes of self.
    self.func=func
    self.args=args
    self.keys=keys
    self.time=time
    self.priority=priority
    # Here we define several variables for latter use.
    self.group=()
    self.cancelled=False
    self.parent=None

  def __cmp__(self,other):
    return cmp((self.time,-self.priority),(other.time,-other.priority))

  def __repr__(self):
    # We can reform the following information as a string
    return '<%s %x %5.3f>'%(self.name,id(self.func),self.time)

class SchedulerError(Exception):
    pass

class Scheduler:
    def __init__(self):
        # Create the list to store the queue of functions to be executed.
        self.queue=[]
        # Create the list to store the functions to be added to the queue.
        self.to_be_added=[]
        # Create the dictionary to store ...
        self.triggers={}
        # Create and set the time delay for to 0.0s for now.
        self.time=0.0
        # Set the stop_flag to False.
        self.stop_flag=False
        #
        self.log=logger.log_proxy

    def extend(self,other):
        for k,v in other.triggers.items():
            if k not in self.triggers:
                self.triggers[k]=v
            else:
                self.triggers[k].extend(v)
        if len(other.queue)>0:
            self.queue.extend(other.queue)
            heapq.heapify(self.queue)

    def trigger(self,key,priority=None):
        # Hint: If the function key is in the list of self.triggers, we add the function execution
        # to the execution queue.
        if key in self.triggers:
            for event in self.triggers[key]:
                event.time=self.time
                if priority is not None:
                   event.priority=priority
                # We add the function execution (event) into the execution queue.
                self.add_event(event)
            del self.triggers[key][:]

    def add_event(self,event):
        # Push the function execution, i.e. "event", into the queue.
        heapq.heappush(self.queue,event)

    def add(self,func,delay=0,args=[],keys={},priority=0,thread_safe=False):
        """Add a function execution to the queue"""
        # If the thread is not safe now, we add the function execution to the _to_be_added list, so it will be added
        # in the future.
        if thread_safe:
          self.to_be_added.append((func,delay,args,keys,priority))
        # If the thread is safe, we can directly push the function execution into the queue.
        else:
          # Let us first wrap (1) the function, (2) the arguments and (3) keywords to the function,
          # (4) the time to execute, and (5) the priority together into an object.
          ev=Event(func,self.time+delay,args=args,keys=keys,priority=priority)
          # This step is important. We add the function execuation to the execution queue.
          self.add_event(ev)
          return ev

    def run(self):
        # We set the stop_flag to False.
        self.stop_flag=False
        # We create a while-loop which stops only when (1) the stop_flag is True, and (2) there is no function execution
        # (event) in the queue.
        while not self.stop_flag and len(self.queue)>0:
            # Denote "next" as the time of the first event is the queue.
            next=self.queue[0].time
            if next>self.time:
                self.time=next
                self.log.time=next
            self.do_event(heapq.heappop(self.queue))
            while self.to_be_added:
              self.add(*self.to_be_added.pop())

    def handle_result(self,result,event):
        """
        Post processing of the function execution.
        :param result: The result of the function execution.
        :param event: It contains the function and the arguments and keywords of the function.
        :return:
        """
        # If the result is a number, according to the design we
        if isinstance(result,(int,float)):
            event.time=self.time+result
            # Hint: The reason which this event is added back to the queue is because the function executed is a generator.
            # That is to say, that function used a "yield" command. In the first round of execution, it yields the delay
            # time. Then, the event is added back to the queue to be executed the second time. In the second round, the
            # execution starts from where it left off in the first round. If you are not familiar with the concept of
            # generator, this is confusing. I was confused for a while. I recommend you figure out what a generator is
            # first.)-->
            self.add_event(event)
        # If the result is a dictionary,
        elif isinstance(result,dict):
            event.time=self.time+result.get('delay',0)
            event.priority=result.get('priority',event.priority)
            # If you are confused about why this event is added back to the queue, please refer to the above hint.
            self.add_event(event)
        elif isinstance(result,(str,Trigger)):
            event.time=None
            if result not in self.triggers:
                # Here we add function executions to the self.triggers dictionary.
                self.triggers[result]=[event]
            else:
                self.triggers[result].append(event)
        elif isinstance(result,(list,tuple)):
            events=[copy.copy(event) for r in result]
            for e in events: e.group=events
            for i,r in enumerate(result):
                self.handle_result(r,events[i])
        elif result is None:
            if event.parent is not None:
                event.parent.time=self.time
                self.add_event(event.parent)
        elif isinstance(result,Event):
            if result.generator and event.generator:
                result.parent=event
        elif hasattr(result,'default_trigger'):
          self.handle_result(result.default_trigger,event)
        else:
            raise SchedulerError("Incorrect 'yield': %s"%(result))

    def do_event(self,event):
        assert self.time==event.time
        # If the function execution (event) is cancelled, we do nothing here.
        if event.cancelled: return
        # If the function execution (event) is not cancelled, (I dont understand it here. I will come be later.)
        for e in event.group: e.cancelled=True
        event.cancelled=False
        # Here, we try to execute the function in the current event with the associated arguments and keywords.
        try:
          result=event.func(*event.args,**event.keys)
        except StopIteration:
          result=None
        # We will handle the result of the function execution using handle_result()
        self.handle_result(result,event)

    def stop(self):
      # Set the stop flag to True.
      self.stop_flag=True

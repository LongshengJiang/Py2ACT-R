# Status: On going...
# Commenter: Longsheng Jiang
# Date: 04/27/2020

from __future__ import generators

from . import scheduler
from . import logger
import random
import inspect
import copy
#import ccm.config as config

class MethodWrapper:
  def __init__(self,obj,func,name):
      self.func=func
      self.obj=obj
      self.func_name=name
      self.begins=scheduler.Trigger(name+' begin')
      self.ends=scheduler.Trigger(name+' end')
      self.default_trigger=self.ends
  def __call__(self,*args,**keys):
      self.obj.sch.trigger(self.begins)
      val=self.func(self.obj,*args,**keys)
      self.obj.sch.trigger(self.ends)
      return val
class MethodGeneratorWrapper(MethodWrapper):
  def _generator(self,*args,**keys):
      self.obj.sch.trigger(self.begins)
      for x in self.func(self.obj,*args,**keys):
          yield x
      self.obj.sch.trigger(self.ends)
  def __call__(self,*args,**keys):
      return self.obj.sch.add(self._generator,args=args,keys=keys)
  def __str__(self):
      return '<MGW %s %s>'%(self.obj,self.func_name)

def log_everything(model,log=None):
  if log is None: log=logger.log_proxy
  if not hasattr(model,'log'): model.run(limit=0)
  model.log=log
  for k,v in model.__dict__.items():
    if k[0]!='_' and k!='parent':
      if isinstance(v,Model) and v.parent is model:
        log_everything(v,getattr(log,k))


class Model:
    # Define a flag to indicate if the object has been converted.
    __converted=False
    _convert_methods=True
    _auto_run_start=True
    name='top'

    def __init__(self,log=None,**keys):
        # Initialize the log
        self.__init_log=log
        for k,v in keys.items():
          setattr(self,k,v)

    def __convert(self,parent=None,name=None):
        #if self.__converted: return
        assert self.__converted==False
        self.__converted=True
        self.changes=scheduler.Trigger()
        # If the current class has the atrribute parent, we get a local copy of the parent.
        if hasattr(self,'parent'): parent=self.parent

        methods={}
        objects={}
        # In the following, we use inspect.getmro to get the baseclasses of the current class.
        # inpsect.getmro(cls) returns a tuple of class cls's base classes, including cls, in method resolution order.
        # No class appears more than once in this tuple.
        # For all the base classes,
        for klass in inspect.getmro(self.__class__):
            # Hint: The class Model defines the framework of Python ACT-R. It is the parent of other classes and is very
            # remote to the users. Hence, we do NOT want to consider it.
            # If the class is not Model,
            if klass is not Model:
                #  Hint: inspect.getmembers(object, [predicate]) returns all the members of an object
                #  in a list of (name, value) pairs sorted by name.
                # For each member, in the form of key-value pair, in the class klass,
                for k,v in inspect.getmembers(klass):
                    # If the key word does not starts with an underscore, a.k.a, the member is not local to the class,
                    if k[0]!='_':
                        # further if the member is a method of the class,
                        if inspect.ismethod(v):
                            # even further if the key name k is not among the following names, and the key name k is not
                            # yet included in the dictionary "methods", and the class klass is not Model.
                            if k not in ['run','now','get_children'] and k not in methods and klass is not Model:
                                # We add the method v into the list "methods".
                                methods[k]=v
                        # If the member is not a method,
                        else:
                            # further if the member v is a class and its base class is Model,
                            if inspect.isclass(v) and Model in inspect.getmro(v):
                                # we let v be an initialization of the class v. Now the new v is an object.
                                v=v()
                            # If the key name k is not yet in the dictionary "objects"
                            if k not in objects:
                                # we add it to the dictionary.
                                objects[k]=v
        # We produce an independent copy of the objects. In the new objects, there is no reference to the original.
        objects=copy.deepcopy(objects)
        # If the current class has parents or if the argument parent of function __convert(self,parent,name) is not None.
        if parent:
            # If the parent object has not been converted, we convert it now with the function __convert()
            if not parent.__converted: parent.__convert()
            # The current object inherits the scheduler from the parent object.
            self.sch=parent.sch
            # We set the log to be dummy. (!!! I will explain it in the future.)
            self.log=logger.dummy
            # The current object inherits the random object from the parent object.
            self.random=parent.random
            # We attach the parent object back to self.
            self.parent=parent
        # If the current class has no parent, :-( a poor orphan,
        else:
            # We define a new scheduler for the current object.
            self.sch=scheduler.Scheduler()
            # (!!! I don't have enough understanding of logger.py. I will return to this latter.)
            if self.__init_log is True:
                self.log=logger.log()
            elif self.__init_log is None:
                self.log=logger.dummy
            else:
                self.log=self.__init_log
            # We create a new random object this the current object.
            self.random=random.Random()
            #(obsolete) seed=config.getOptions().random
            #(obsolete) if seed is not None: self.random.seed(seed)
            # We confirm that the current object has no parent.
            self.parent=None
        # We can further process the objects and methods obtained from the conversion.
        self._convert_info(objects,methods)
        # For each name-object pair in the dictionary "objects",
        for name,obj in objects.items():
            # if the object is an instance of the Model class,
            if isinstance(obj,Model):
                # further if this object has not been converted, we convert the object now.
                # Recall now the current object "self" is the parent of "obj".
                if not obj.__converted:
                    obj.__convert(self,name)
                # if this object has been converted, we change the name to its current name.
                else:
                    obj.name=name
                # We try to officially adopt obj as a child of the current object.
                try:
                  self._children[name]=obj
                # In the case that the dictionary _children is not created, we created the dictionary here.
                except AttributeError:
                  self._children={name:obj}
            # Lastly, we add obj to the __dict__ dictionary.
            self.__dict__[name]=obj
        # If the methods need to be further converted,
        if self._convert_methods:
          # for each name-function pair in the dictionary "methods",
          for name,func in methods.items():
              # if the function is a generator,
              if func.im_func.func_code.co_flags&0x20==0x20:
                  # we wrap the function into an object.
                  w=MethodGeneratorWrapper(self,func,name)
              # If the function is not a generator,
              else:
                  # we wrap the function into an object.
                  w=MethodWrapper(self,func,name)
              # Lastly, we add the function object into __dict__ dictionary.
              self.__dict__[name]=w
        # If the start() function needs to be autonmatically run,
        if self._auto_run_start:
            # We automatically run the function start().
            self.start()
        # For each member in __dict__ dictionary, in the form of key-value pair,
        for k,v in self.__dict__.items():
            # if the object is not local, the object is not parent, and the object is an instance of class Model,
            if k[0]!='_' and k!='parent' and isinstance(v,Model):
                # further if the object has not been converted, we convert it now.
                if not v.__converted:
                    v.__convert(parent=self)


    def _convert_info(self,objects,methods):
        pass

    def __setattr__(self,key,value):
      # Add a new attribute to the object
      # If the key is parent without a value, but the object already has a parent, we let the current object's parent
      # disclaim the current object as her child.
      if key=='parent' and value is None and getattr(self,'parent',None) is not None:
        del self.parent._children[self.name]
      # We then add the key-value pair as a new member to __dict__ dictionary.
      self.__dict__[key]=value
      # If the new member is an instance of class Model, the new member is not private, and its is not a parent,
      if isinstance(value,Model) and key[0]!='_' and key!='parent':
        # We make sure the current object has been converted.
        self._ensure_converted()
        # Let p as the current object.
        p=self
        ancestor=True
        # While the current object is not empty, we do the following.
        while p is not None:
          ## This block checks if value is parent of the current object self.
          # If the added new attribute is self or a parent of self, we should directly jump out of the while-loop now.
          if value is p: break
          # We go to find the parent of the current object, and let the parent be p. If no parent, p becomes None.
          p=getattr(p,'parent',None)
        # If value is not a parent of the current object self,
        else:
          # further if value has a parent, we do nothing.
          if getattr(value,'parent',None) is not None:
            pass
            #(obsolete) if value.name in value.parent._children:
            #(obsolete)  del value.parent._children[value.name]
          # if value has no parent,
          else:
            # The current object self adopts value as her child; value's parent is self.
            value.parent=self
            # We give value a name. This name is the key name in the key-value pair when value is adopted.
            value.name=key
            # We try to claim value as self's new child.
            try:
              self._children[key]=value
            # In the case self has no family yet, we create a family with the new adopted child for self.
            except AttributeError:
              self._children={key:value}
            # If the current object is converted, but value has not been converted, we convert the value.
            if self.__converted and not value.__converted: value.__convert(name=key,parent=self)
      # If the current object self is converted, the new attribute is not to be private, and the key is not among the
      # following list,
      if self.__converted and key[0]!='_' and key not in ['parent','sch','changes','log','random','name']:
          # We give self a nickname m.
          m=self
          # Create a empty list for storing ...
          done=[]
          # The following while-loop scans the parents of the current object self. At each level in the hierarchy, the
          # function execution (events) are added to the execution queue.
          while m is not None:
            self.sch.trigger(m.changes,priority=-1)
            done.append(m)
            m=m.parent
            if m in done: m=None
          if self.log: setattr(self.log,key,value)

      if key=='log' and value is not None:
        for k,v in self.__dict__.items():
          if k[0]!='_' and k not in ['parent','sch','changes','log','random','name']:
            if isinstance(v,(int,str,float,type(None))):
              setattr(value,k,v)




    def start(self):
        pass
    def run(self,limit=None,func=None):
        if not self.__converted:
            self.__convert()
        #if config.getOptions().logall: log_everything(self)
        if limit is not None:
            self.sch.add(self.sch.stop,limit,priority=-9999999)
        if func is not None:
            self.sch.add(func)
        self.sch.run()
    def stop(self):
        if not self.__converted:
            self.__convert()
        self.sch.stop()
    def now(self):
        if not self.__converted:
            self.__convert()
        return self.sch.time

    def get_children(self):
        try:
          return self._children.values()
        except AttributeError:
          return []


    def _get_scheduler(self):
        self._ensure_converted()
        return self.sch

    def _ensure_converted(self):
        if not self.__converted:
            self.__convert()

    def _is_converted(self):
        return self.__converted













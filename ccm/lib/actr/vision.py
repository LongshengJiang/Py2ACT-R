import ccm

from ccm.pattern import Pattern
from ccm.lib.actr.dm import Finst
from ccm.lib.actr.buffer import Chunk

class Vision(ccm.Model):
  def __init__(self,visual,location):
    ccm.Model.__init__(self)
    self._visual=visual
    self._location=location
    self.busy=False
    self.lastLocationPattern=Pattern('')
    self.tracking=None
    self.timeAppeared={}
    self.visualOnsetSpan=0.5
    self.finst=Finst(self)   
    
  def start(self):
    self.environmentUpdate()
    
  def isNew(self,object):
    if not getattr(object,'visible',True): return
    time=self.timeAppeared.get(object,None)
    if time==None:
      self.timeAppeared[object]=self.now()
      return True
    return self.now()<time+self.visualOnsetSpan
    
  def environmentUpdate(self):
    # First, create a while-loop for checking updates to the environment.
   while True:
     # If the visual location buffer is empty,
    if self._location.isEmpty():
      # Create a list for storing new visible objects in the environment.
      r=[]
      # In the following self is the vision module, self.parent is the agent which includes the vision module,
      # and self.parent.parent is the environment in which the agent is.
      for o in self.parent.parent.get_children():
        # If the object is not visible anymore,
        if not getattr(o,'visible',True):
            # further if the object is in timeAppeared, then we delete the object from timeAppeared.
            # Note timeAppeared records the time when an object becomes visible in the environment.
            if o in self.timeAppeared.keys(): del self.timeAppeared[o]
            # Let us go to check the next object in the environment directly.
            continue
        # If the object is not in timeAppeared,
        if o not in self.timeAppeared:
          # further if the object has the location information,
          if hasattr(o,'x') and hasattr(o,'y'):  
            #(obsolete) if self.lastLocationPattern.match(o)!=None:
              # Let add this object into the list r.
              r.append(o)
      # If there is new visible objects, i.e., the list is not empty,
      if len(r)>0:
        # We randomly select one object.
        obj=self.random.choice(r)
        # We print the following information to the display.
        self.log._='Vision stuffed obj at (%g,%g)'%(obj.x,obj.y)
        # We add the location of the new visible object to the visual location buffer.
        self._location.set('%g %g'%(obj.x,obj.y))
    
    #(obsolete) print 'checking tracking',self.tracking
    #(obsolete) if self.tracking!=None and (self.tracking not in self.parent.parent.get_children() or not getattr(self.tracking,'visible',True)):
    #(obsolete)  print '...lost'
    #(obsolete)  self.sch.add(self.lostTrack,delay=0.085)

     # In the following self is the vision module, self.parent is the agent which includes the vision module,
     # and self.parent.parent is the environment in which the agent is. In the for-loop, each object in the environment
     # is checked to see if they are new visiable objects.
    for o in self.parent.parent.get_children():    
      self.isNew(o)
    # In the following self is the vision module, self.parent is the agent which includes the vision module,
    # and self.parent.parent is the environment in which the agent is.
    yield self.parent.parent.changes,self.lostTrack
   
  def lostTrack(self):
    """Indicate that the vision tracking is lost."""
    # If the vision module is tracking an object,
    if self.tracking is not None:
      # The object slips away from our tracking.
      self.tracking=None
      # We print the information to the display.
      self.log._='Object disappeared'
      # And we clear the visual buffer.
      self._visual.clear()
      #(obsolete) self._location.clear()

    
  def attendToUnattended(self,pattern=''):
    self.attendTo(pattern=pattern,unattended=True)
  def attendToNew(self,pattern=''):
    self.attendTo(pattern=pattern,new=True)

  def attendTo(self,pattern,unattended=False,new=False):
    # The argument "pattern" contains the information of a visual location.
    # If pat provides only the values of x-coordinate and y-coordinate,
    # we reorganize pat into 'x: x-coordinate y: y-coordinate'.
    if isinstance(pattern, str) and ':' not in pattern and pattern.count(' ')==1:
        pattern='x:%s y:%s'%tuple(pattern.split(' '))
    # The x-coordinate, y-coordinate often are variables, e.g. "?x ?y". We use function Pattern() to map
    # the variables to the values stored in sch.bound.
    self.lastLocationPattern=Pattern(pattern,self.sch.bound)
    r=[]
    # In the following self is the vision module, self.parent is the agent which includes the vision module,
    # and self.parent.parent is the environment in which the agent is. In the for-loop, each object in the environment
    # is checked to see if they are visiable objects.
    for obj in self.parent.parent.get_children():
      # If the visual location is new, but the object is not new, we directly go to check the next object.
      if new==True and not self.isNew(obj): continue
      # If the location is unattended, but the object is in finst (finger instantiation) list, we directly go to check
      # the next object.
      if unattended==True and self.finst.isIn(obj): continue
      # Let us check if an object is a visible object. We do so by checking if the object contains the attributes
      # "x", "y", and if the attribute "visible=True".
      if hasattr(obj,'x') and hasattr(obj,'y') and getattr(obj,'visible',True):
        # Further, if the visual location matches the location of the visible object,
        if self.lastLocationPattern.match(obj)!=None:
          # We add this object to the list r.
          r.append(obj)
    # If we found more than one visible objects in the list r,
    if len(r)>0:
      # We randomly chose one object from the list.
      obj=self.random.choice(r)
      # We print the following information to the display.
      self.log._='Vision found obj at (%g,%g)'%(obj.x,obj.y)
      # We store the object's location into the visual location buffer. 
      self._location.set('%g %g'%(obj.x,obj.y))

  def isClose(self,a,b):
      return abs(a-b)<0.01

  def examine(self,pat):
    """
    Check the visible object at a visual location.
    :param pat: specify the visual location.
    :return:
    """
    # The argument "pat" (pattern) contains the information of a visual location.
    # If pat provides only the values of x-coordinate and y-coordinate,
    # we reorganize pat into 'x: x-coordinate y: y-coordinate'.
    if isinstance(pat, str) and ':' not in pat and pat.count(' ')==1:
        pat='x:%s y:%s'%tuple(pat.split(' '))
    # The x-coordinate, y-coordinate often are variables, e.g. "?x ?y". We use function Pattern() to map
    # the variables to the values stored in sch.bound.
    self.lastExamine=Pattern(pat,self.sch.bound)
    # Now we update the variable pat which has assigned valules.
    pat=self.lastExamine
    # In the following self is the vision module, self.parent is the agent which includes the vision module,
    # and self.parent.parent is the environment in which the agent is. In the for-loop, each object in the environment
    # is checked to see if they are visiable objects.
    for obj in self.parent.parent.get_children():
     # First, let us check if an object is a visible object. We do so by checking if the object contains the attributes
     # "x", "y", and if the attribute "visible=True".
     if hasattr(obj,'x') and hasattr(obj,'y') and getattr(obj,'visible',True):   
      # Further, if the visual location pat matches the location of the visible object,
      if pat.match(obj) is not None:
      #(obsolete) if self.isClose(obj.x,float(pat[0])) and self.isClose(obj.y,float(pat[1])):
        # The vision module starts working; it is busy.
        self.busy=True
        # The default time required for a vision module request is set as 0.085s.
        yield 0.085
        # The vision module finishes working; it is not busy.
        self.busy=False
        # In the following, self is the vision module, self.parent is the agent which includes the vision module,
        # and self.parent.parent is the environment in which the agent is.
        # If obj is still an object in the environment,
        if obj in self.parent.parent.get_children():
          # The vision module is tracking this object.
          self.tracking=obj
          # We print the following information to the display.
          self.log._='Vision sees %s'%Chunk(obj)
          # We put the object into the visual buffer.
          self._visual.set(obj)
          # We add the object into the list of finst (finger instantiation).
          self.finst.add(obj)
        # If obj is no longer an object in the environment,
        else:
          # There is nothing to track.
          self.tracking=None
          # We print the following information to the display.
          self.log._='Vision sees nothing'
          # We clear the visual buffer.
          self._visual.clear()
        # Each time, only one object can be seen. When we find one, we break the for-loop.
        break  


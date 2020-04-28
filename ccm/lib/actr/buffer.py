import ccm

try:
    from UserDict import UserDict
except:
    from collections import UserDict


class Chunk(UserDict):
  """Create a dictionary to store name-value pairs"""
  def __init__(self,contents,bound=None):
    # We first initialize the UserDict.
    UserDict.__init__(self)
    # If the contents is already in the form of a chunk, we update the current chunk with the name-value pairs in
    # the contents.
    if isinstance(contents,Chunk):
      self.update(contents)
    # If the contents is in the form of a string,
    elif isinstance(contents,str):
      # We split the string by space. This create a list of string elements.
      # For each element x and its index i,
      for i,x in enumerate(contents.split()):
        # if there is ":" in element x, then x is a name-value pair. We split this name-value pair and denote the name
        # as i and the value as the new x.
        if ':' in x:
          i,x=x.split(':',1)
        # If x (or the new x) starts with "?", it means x is a variable in the from of "?xxx". In this case, we need
        # to retrieve the value of the variable.
        if x.startswith('?'):
          # Let the string after "?" to be the key for retrieving the variable value.
          key=x[1:]
          # Retrieve the variable value from "bound". Note if there is a variable, the value of the variable must
          # have been defined before. Hence, "bound" here will not be None.
          x=bound[key]
        # We now save the retrieved name-value pair into the chunk. Note that index i may be int.
        self[i]=x
    # If the contents is a dictionary,
    elif hasattr(contents,'__dict__'):
      # We retrieve the key-value pairs using a for-loop.
      for k,v in contents.__dict__.items():
        # If the type of the value is among the four following types,
        if type(v) in [str,float,int,bool]:
          # Save the key-value pair into the chunk.
          self[k]=v
    # For other types of contents,
    else:
      # let us directly try to update the current chunk with the contents.
      try:
        self.update(contents)
        # It may raise an exception, if the current chunk cannot be updated.
      except:  
        raise Exception('Unknown contents for chunk:',contents)      
  def __repr__(self):
    # Create a list for storing the organized information of the chunck.
    r=[]
    # Let us collect all the keys of the current chunk in a list.
    keys=self.keys()
    # Define an int index.
    i=0
    # As long as the index is an int, we add the value as a string to the list r.
    while i in keys:
      r.append('%s'%self[i])
      # Remove this int key from the list keys.
      keys.remove(i)
      i+=1
    # After the above while-loop, there is no int in the list keys. We sort the keys in the list.
    keys.sort()
    # For each key k in the list keys, if it does not start with '_', we append the key-value pair in the form of
    # "name:value" to the list r.
    for k in keys:
      if k[0]!='_':
        r.append('%s:%s'%(k,self[k]))
    # Finially, let us use a space as the seperator to join the elements in the list r into a string.
    return ' '.join(r)  
      

class Buffer(ccm.Model):
  def __init__(self):
    # Create the variable for storing a chunk.
    self.chunk=None

  def set(self,chunk):
    """Add a chunk of information into the buffer"""
    # Try to create the chunk of information. Here we use function Chunk() to reshape the information into a dictionary.
    try:
      self.chunk=Chunk(chunk,self.sch.bound)
    except AttributeError:
      # In the case that there is variables defined in the input argument "chunk", there is to self.sch.bound defined.
      # Hence, we put {} for the second argument.
      self.chunk=Chunk(chunk,{})

  def modify(self,**args):
    """Modify the information in the buffer."""
    # For the key-value pairs in the args,
    for k,v in args.items():
      # if the key starts with an underscore "_", then the key uses an int as the index. We recover the int key from
      # the original string key.
      if k.startswith('_'): k=int(k[1:])
      # If the key is not in the dictionary self.chunk, we raise an exception saying there is no such slot.
      if k not in self.chunk:
        raise Exception('No slot "%s" to modify to "%s"'%(k,v))
      # We then update the value index by the key k.
      self.chunk[k]=v
      self.chunk=self.chunk

  def __getitem__(self,key):
    # This function return the value indexed by the key.
    return self.chunk[key]

  def clear(self):
    """Clear the buffer entirely."""
    # Clear the chunk.
    self.chunk=None

  def __eq__(self,other):
    """Check if the info in the buffer is the same"""
    # Return True if the chunk equals other; return False if the chunk does not equal other.
    return self.chunk==other

  def __hash__(self):
    return id(self)

  def __len__(self):
    if self.chunk is None: return 0
    return len(self.chunk)

  def isEmpty(self):
    """Check if the buffer is empty."""
    # Return True if the buffer is empty; return False if the buffer is not empty.
    return len(self)==0

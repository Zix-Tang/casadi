"""

This script generates parts of CasADi source code that are highly repetitive and easily automated

"""
import os, fnmatch
import re

def locate(pattern, root=os.curdir):
    """
    Locate all files matching supplied filename pattern in and below
    supplied root directory.
    """
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)
            
            
# Part 1:    helper functions for inputs/outputs


# Some regexes
re_introIn = re.compile("/// (Input arguments .*) \[(\w+)\]")
re_introOut = re.compile("/// (Output arguments .*) \[(\w+)\]")
re_doc = re.compile("///\s*(.*) \[([\w\d]+)\]\s*")
re_docraw = re.compile("///\s*(.*)")
re_enumheader = re.compile("enum (\w+)\s*{")
re_enum = re.compile("\s*(\w+),\s*")
re_end = re.compile("}\s*;")

class Enum:
  def __init__(self,name, doc):
    self.name    = name
    self.doc     = doc + "\n"
    self.entries = []
  
  def addArg(self, name, doc):
    self.entries.append([name,doc])

  def getDoc(self):
    return self.doc.replace("\\n","")

  def addDoc(self,doc):
    self.doc+=doc + "\n"
  
  def addEnum(self, enum):
    if len(self.entries[-1])>2:
      raise Exception("Enum %s already given" % enum)
    self.entries[-1].append(enum)
      
  def addEnumheader(self,header):
    self.enum = header
    
  def __str__(self):
    s = self.name + "(" + self.doc + ")" + "[" + self.enum  + "]" + ": " + str(self.entries)
    return s
    
  def checkconsistency(self):
    for e in self.entries:
      if not(len(e))==3:
         raise Exception("Consistency")
    
    assert(self.enum.endswith(self.__class__.__name__))
    prefix = self.enum[:-len(self.__class__.__name__)]
    
    for name, doc, enum in self.entries:
      assert(enum.startswith(enum))
      assert(not("_NUM_" in enum))
      
  def num(self):
    #return self.enum[:-len(self.__class__.__name__)] +  "_NUM_" + self.PRE
    return str(len(self.entries))
      
  def cppcode(self):
    s = "/// Helper function for '" + self.enum + "'\n"
    s+= "\n".join(map(lambda x: "/// " + x.rstrip(),self.doc.split("\n")))+"\n"
    s+= "/// \\copydoc scheme_" + self.enum +  "\n"
    s+= "template<class M>" + "\n"
    s+= "std::vector<M> " + self.name + "("
    for name, doc, enum in self.entries:
      s+="const M& " + name + "=M()" + ","
    s=s[:-1] + "){" + "\n"
    s+="  M ret[" + self.num() + "] = {"
    for name, doc, enum in self.entries:
      s+=name+","
    s=s[:-1] + "};\n"
    s+= "  return std::vector<M>(ret,ret+" +  self.num() + ");"
    s+="\n}\n"
    return s
    
  def swigcode(self):
    s="namespace CasADi {\n"
    s+="%template(" + self.name + ") " + self.name + "<SXMatrix>;\n"
    s+="%template(" + self.name + ") " + self.name + "<MX>;\n"
    s+="}\n"
    return s
    
  def pycode(self):
    s="def " + self.name + "("
    for name, doc, enum in self.entries:
      s+=name+"=[],"
    s=s[:-1] + "):\n"
    s+='  """\n'
    s+= "  Helper function for '" + self.enum + "'\n\n"
    s+= "\n".join(map(lambda x: "  " + x.rstrip(),self.getDoc().split("\n"))) + "\n"
    s+= "  Keyword arguments:\n"
    maxlenname = max([len(name) for name, doc, enum in self.entries])
    for name, doc, enum in self.entries:
      s+="    " + name + (" "*(maxlenname-len(name))) +  " -- " +  doc + " [" + enum + "]\n"
    s+='  """\n'
    s+="  return ["
    for name, doc, enum in self.entries:
      s+=name+","
    s=s[:-1] + "]\n"
    return s
  
class Input(Enum):
  PRE = "IN"
  tp = "Input"
  pass
  
class Output(Enum):
  PRE = "OUT"
  tp = "Output"
  pass

autogencpp = file(os.path.join(os.curdir,"..","casadi","autogenerated.hpp"),"w")
autogenpy = file(os.path.join(os.curdir,"..","swig","autogenerated.i"),"w")

autogencpp.write(file('license_header.txt','r').read())
autogencpp.write("/** All edits to this file will be lost - autogenerated by misc/autogencode.py */\n")
autogencpp.write("#ifndef AUTOGENERATED_HPP\n#define AUTOGENERATED_HPP\n#include <vector>\nnamespace CasADi{\n")
autogenpy.write(file('license_header.txt','r').read())
autogenpy.write("/** All edits to this file will be lost - autogenerated by misc/autogencode.py */\n")
autogenpy.write("""%include "casadi/autogenerated.hpp"\n""")
for h in locate("*.hpp",os.path.join(os.curdir,"..")):
  f =  file(h,'r')
  while 1:
    line = f.readline()
    if not(line):
      break 
    p = None
    m = re.match(re_introIn,line)
    if m:
      p = Input(m.group(2),m.group(1))
    m = re.match(re_introOut,line)
    if m:
      p = Output(m.group(2),m.group(1))
    if p:
      line = f.readline()
      while re.search(re_docraw, line):
        p.addDoc(re.search(re_docraw,line).group(1))
        line = f.readline()

      while not(re.search(re_end, line)):
        mm = re.search(re_doc, line )
        if mm:
          p.addArg(mm.group(2),mm.group(1))
        mm = re.match(re_enum, line )
        if mm:
          p.addEnum(mm.group(1))
        mm = re.match(re_enumheader, line )
        if mm:
          p.addEnumheader(mm.group(1))
        line = f.readline()
      p.checkconsistency()
      print p.name
      autogencpp.write(p.cppcode())
      autogenpy.write("%pythoncode %{\n")
      autogenpy.write(p.pycode())
      autogenpy.write("%}\n")
      autogenpy.write("#ifndef SWIGPYTHON\n")
      autogenpy.write(p.swigcode())
      autogenpy.write("#endif //SWIGPYTHON\n")
      
autogencpp.write("}\n#endif //AUTOGENERATED_HPP\n")


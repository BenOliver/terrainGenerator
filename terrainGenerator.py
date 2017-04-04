import bpy
import bmesh
import time
from math import *
from random import random
C=bpy.context
D=bpy.data
M=D.meshes
O=D.objects

class terrain:
    '''a blender object which represents a landscape heightmap'''
    
    
    def __init__(self, name, meshName=None, objectName=None, matName=None):
        self.origin=[0,0,0]
        self.name=name
        self.meshName=meshName
        self.objectName=objectName
        self.matName=matName
        #create names
        if self.meshName is None:
            self.meshName=self.name +"Mesh"
        if self.objectName is None:
            print("objectName is None")
            self.objectName=self.name+"Object"
        if self.matName is None:
            self.matName=self.name+"Mat"
            
        #cleanup older versions if they exist
        self.delMesh(self.meshName)
        self.delObject(self.objectName)
        self.delMaterial(self.matName)
        
        #create new mesh
        self.me=M.new(self.meshName)
        
        #create object and link mesh
        self.ob=O.new(self.objectName,self.me)
        #give object location and link to scene
        self.ob.location=self.origin
        C.scene.objects.link(self.ob)
        
        
        #create material and link to mesh
        self.mat=D.materials.new(self.matName)
        self.me.materials.append(self.mat)
        self.mat.use_vertex_color_paint=1


        #create bmesh
        self.bm=bmesh.new()
        self.bm.from_mesh(self.me)
        self.V=self.bm.verts
        self.E=self.bm.edges
        self.F=self.bm.faces
        
    def genMesh(self):
        Hardness=2
        hardFactor=0.8
        
        #set level of detail. exponentially sensitive. values greater than 2**7 take longer than 1 second to compute
        terrSize=2**9   #sets level of detail
        
        terrScale=10 #(was 100?)
        zAmp=1
        
        #create the square grid of terrSize x terrSize squares
        v=[0]*(terrSize+1)
        for i in range(0,len(v)):
            v[i]=[0]*(terrSize+1)


        #create temporary grid to aid in generating                    
        vt=[0]*(terrSize+1)
        for i in range(0,len(v)):
            vt[i]=[0]*(terrSize+1)
            
        #initialize initial corner vertices
        vt[0][0]=0
        vt[0][-1]=0
        vt[-1][0]=0
        vt[-1][-1]=0
        
      
        worldSeed=floor(random()*1000)
        print('the seed is {}'.format(worldSeed))
        
        def fudge(seed):
            #TODO: replace with standard library random generator
            seed1=seed
            seed2=5
            prime1=96002369
            prime2=15646879
            prime3=10007
            #use the primes and world seed (worldSeed) to generate a random number based on the x and y coordinates. noiz is between 0 and 1.
            noiz1=(((prime1*i*terrScale/terrSize+prime2*j*terrScale/terrSize+seed1)**seed2)%prime3)/prime3
            #repeat process using first result
            noiz=(((noiz1*prime1*i*terrScale/terrSize+prime2*j*terrScale/terrSize+seed1)**seed2)%prime3)/prime3
            #TODO: check if noiz1 should also be on the j coord
            
            return (Hardness*(squareSize**hardFactor)*(noiz-0.5))
            #the -0.5 balances the heighmap around the midplane
        
        squareSize=terrSize
        numSquares=terrSize/squareSize
        #start with the original square and progress to smaller squares until at the smallest.
        while squareSize>=2:
            r=int(squareSize/2)
            if squareSize==terrSize:
                div=3
            else:
                div=4
            sqS=int(squareSize)
            for i in range(r, terrSize, squareSize):
                for j in range(r, terrSize, squareSize):
                    v[i][j]=(fudge(worldSeed)+v[i-r][j-r]+v[i+r][j+r]+v[i+r][j-r]+v[i-r][j+r])/4
                    
            for i in range(r,terrSize+1,squareSize):
                for j in range(0,terrSize+1,squareSize):
                    if j==terrSize:
                        v[i][j]=v[i][0]
                    else:
                            v[i][j]=(fudge(worldSeed)+v[(i+r)%terrSize][j]+v[(i-r)%terrSize][j]+(div-3)*v[i][(j+r)%terrSize]+v[i][(j-r)%terrSize])/div

            
            for i in range(0,terrSize+1,squareSize):
                for j in range(r,terrSize+1,squareSize):
                    if i==terrSize:
                        v[i][j]=v[0][j]
                    else:
                            v[i][j]=(fudge(worldSeed)+(div-3)*v[(i+r)%terrSize][j]+v[(i-r)%terrSize][j]+v[i][(j+r)%terrSize]+v[i][(j-r)%terrSize])/div
            
            squareSize=int(squareSize/2)
            
            
            
        for i in range(0,terrSize+1):
            for j in range(0,terrSize+1):
                vt[i][j]=self.V.new((i*terrScale/terrSize, j*terrScale/terrSize, zAmp*v[i][j]*terrScale/terrSize))


        self.f=[]
        for i in range(0,len(vt)-1):
            for j in range(0, len(vt[i])-1):
                self.f.append(self.F.new((vt[i][j],vt[i+1][j],vt[i+1][j+1],vt[i][j+1])))
                
        self.bm.to_mesh(self.me)
                    
                
    
    def delMesh(self,delTarget):
        if delTarget in M:
            #if the mesh already exists, delete it and create it again
            M[delTarget].user_clear()    #clear users from the mesh to allow deletion
            M.remove(M[delTarget])
    
    def delObject(self,delTarget):
        if delTarget in C.scene.objects:
            #if the object is already in the scene unlink it (this is required for deletion)
            C.scene.objects.unlink(C.scene.objects[delTarget])
        if delTarget in O:
            O[delTarget].user_clear()
            O.remove(O[delTarget])
            
    def delMaterial(self,delTarget):
        if delTarget in D.materials:
            #clear users and delete object
            D.materials[delTarget].user_clear()
            D.materials.remove(D.materials[delTarget])
        
    #def genHeightMap(mesh):
        
        
  
    
                
            
    
    #def createMesh(self)    
if __name__ == '__main__':
    ter=terrain("test2")
    ter.genMesh()

    
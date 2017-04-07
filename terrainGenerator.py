import bpy
import bmesh
import time
import statistics
from math import *
from random import random
C=bpy.context
D=bpy.data
M=D.meshes
O=D.objects

noizArray=[]

class Terrain:
    '''a blender object which represents a landscape heightmap'''
    
    Dbug=False          #for debugging. value of 1 to print logs
    def __init__(self, name, meshName=None, objectName=None, matName=None):
        self.tesselate=True
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
    
    def dprint(*args):
        if Terrain.Dbug==True:
            print(args)
    
    def genMesh(self,roughness=1, roughFactor=1,terrPower=9, terrScale=10,zAmp=1):
        
        #self.roughness=roughness      #changes the baseline 'Roughess' TODO:change name
        #self.roughFactor=roughFactor #changes how strong the roughness is (sensitive-keep around 1.0)
        #self.terrPower=terrPower
        terrSize=2**terrPower     #set level of detail. exponentially sensitive. 
                                            #values greater than 2**7 take longer than 1 second to compute
        #self.terrScale=terrScale
        #self.zAmp=zAmp
        
        
        #terrSize=2**8   #sets level of detail
        
        #terrScale=10 # the grid is initially 2x2 (same as blender cube) unless otherwise scaled 
        #zAmp=1  #this scales in only the z direction
        
        #create the square grid of terrSize x terrSize squares
        v=[None]*(terrSize+1)
        for i, item in enumerate(v):
            v[i]=[None]*(terrSize+1)


        #create temporary grid to aid in generating                    
        vt=[0]*(terrSize+1)
        for i, item in enumerate(vt):
            vt[i]=[0]*(terrSize+1)
            
        #initialize initial corner vertices
        v[0][0]=0
        v[0][-1]=0
        v[-1][0]=0
        v[-1][-1]=0
        
        
        vt[0][0]=0
        vt[0][-1]=0
        vt[-1][0]=0
        vt[-1][-1]=0
      
        worldSeed=floor(random()*1000)
        if Terrain.Dbug:
            print('the seed is {}'.format(worldSeed))
        
        def fudge(x,y,r,seed):
            #TODO: replace with standard library random generator
            seed1=seed
            seed2=5
            prime1=96002369
            prime2=15646879
            prime3=10007
            #use the primes and world seed (worldSeed) to generate a random number based on the x and y coordinates. noiz is between 0 and 1.
            noiz1=(((prime1*x*terrScale/terrSize+prime2*y*terrScale/terrSize+seed1)**seed2)%prime3)/prime3
            #repeat process using first result
            #noiz=(((noiz1*prime1*x*terrScale/terrSize+prime2*y*terrScale/terrSize+seed1)**seed2)%prime3)/prime3
            #TODO: check if noiz1 should also be on the j coord
            noizArray.append(noiz1)
            #print('noiz1 is:{}'.format(noiz1))
            #return (roughness*((2*r)**roughFactor)*(noiz1-0.5))
            return roughness*(r**1.0)*(noiz1-0.5)
            #the -0.5 balances the heighmap around the midplane
        
        r=int(terrSize/2)
        numSquares=terrSize/(2*r)
        #start with the original square and progress to smaller squares until at the smallest.
        #uses diamond square algorithm to generate new height values
        
        def diamond(matrix, x, y, r):
            ''' 
            c-------d
            | \   / |
            |   v   |
            | /   \ |
            a-------b
            v is in center.
            value is calculated from the average of the corners, plus a random value
            squareSize is the distance between a and b (or d-c, d-b, c-a)
            '''
            xNeg=x-r
            xPos=x+r
            yNeg=y-r
            yPos=y+r
            a=matrix[xNeg][yNeg]
            b=matrix[xPos][yNeg]
            c=matrix[xNeg][yPos]
            d=matrix[xPos][yPos]
            if Terrain.Dbug:
                print('\ndiamond x:{},y:{}'.format(x,y))
                print('The radius is {}'.format(r))
                print('\tv[{}][{}] = {}'.format(xNeg,yNeg,a))
                print('\tv[{}][{}] = {}'.format(xPos,yNeg,b))
                print('\tv[{}][{}] = {}'.format(xNeg,yPos,c))
                print('\tv[{}][{}] = {}'.format(xPos,yPos,d))
            v=(a+b+c+d)/4+fudge(x,y,r,worldSeed)
            #v=(a+b+c+d+fudge(x,y,r,worldSeed))/5
            if Terrain.Dbug:
                print('v[{}][{}] = {}'.format(x,y,v))        
            self.dprint('it','worked')
            return v
        
        def square(matrix, x, y, r):
            '''
            ----d----
            |   |   |
            b---v---c
            |   |   |
            ----a----
            '''
            div=4
            #performing a modulus operation on the coordinates allows the terrain to be tesselated
            #the pattern loops around the grid (like the asteroid game)
            if self.tesselate:
                xSeed=x%terrSize
                ySeed=y%terrSize
                xNeg=(x-r)%terrSize
                xPos=(x+r)%terrSize
                yNeg=(y-r)%terrSize
                yPos=(y+r)%terrSize

                a=matrix[x][yNeg]
                b=matrix[xNeg][y]                
                c=matrix[xPos][y]
                d=matrix[x][yPos]
            else:
                xNeg=(x-r)
                xPos=(x+r)
                yNeg=(y-r)
                yPos=(y+r)
                         
                if 0<y<terrSize:
                    a=matrix[x][yNeg]
                    d=matrix[x][yPos]
                elif y==0:
                    a=0
                    d=matrix[x][yPos]
                    div=3
                elif y==terrSize:
                    a=matrix[x][yNeg]
                    d=0
                    div=3
                    
                if 0<x<terrSize:
                    b=matrix[xNeg][y]
                    c=matrix[xPos][y]
                elif x==0:
                    b=0
                    c=matrix[xPos][y]
                    div=3
                elif x==terrSize:
                    b=matrix[xNeg][y]
                    c=0
                    div=3
                    
            

            v=(a+b+c+d)/div+fudge(xSeed,ySeed,r,worldSeed)
            #v=(a+b+c+d+fudge(xSeed,ySeed,r,worldSeed))/(div+1)
            return v
                
        while r>=1:
            #r is 'radius'
            if 2*r==terrSize:
                div=3
            else:
                div=4
                
            #diamond step
            for y in range(r, terrSize, 2*r):
                for x in range(r, terrSize, 2*r):
                    v[x][y]=diamond(v,x,y,r)

            #square step                    
            for y in range(0, terrSize+1, r):
                if y%(2*r)==0:
                    start=r
                else:
                    start=0
                #print('y is {}.\nstarting at {}'.format(y,start))
                for x in range(start, terrSize+1, 2*r):
                    v[x][y]=square(v,x,y,r)
                
            
            
            
              
#            for i in range(r,terrSize+1,squareSize):
#                for j in range(0,terrSize+1,squareSize):
#                    if j==terrSize:
#                        v[i][j]=v[i][0]
#                    else:
#                            v[i][j]=(fudge(i,j,worldSeed)+\
#                                v[(i+r)%terrSize][j]+\
#                                v[(i-r)%terrSize][j]+\
#                                v[i][(j+r)%terrSize]*(div-3)+\
#                                v[i][(j-r)%terrSize])/div
#
#            
#            for i in range(0,terrSize+1,squareSize):
#                for j in range(r,terrSize+1,squareSize):
#                    if i==terrSize:
#                        v[i][j]=v[0][j]
#                    else:
#                            v[i][j]=(fudge(i,j,worldSeed)+\
#                                v[(i+r)%terrSize][j]*(div-3)+\
#                                v[(i-r)%terrSize][j]+\
#                                v[i][(j+r)%terrSize]+\
#                                v[i][(j-r)%terrSize])/div
            
            r=int(r/2)
            #squareSize=int(squareSize/2)
            
            
            
        for i in range(0,terrSize+1):
            for j in range(0,terrSize+1):
                vt[i][j]=self.V.new((i*terrScale/terrSize, j*terrScale/terrSize, zAmp*v[i][j]*terrScale/terrSize))


        self.f=[]
        for i in range(0,len(vt)-1):
            for j in range(0, len(vt[i])-1):
                self.f.append(self.F.new((vt[i][j],vt[i+1][j],vt[i+1][j+1],vt[i][j+1])))
                
        self.bm.to_mesh(self.me)
                    
    def assignColors(self):
        vColor=[]
        max=0
        min=0
        
        #save z points to array, calculate max and min heights
        for i in self.me.vertices:
            z=i.co.z
            if z>max:
                max=z
            if z<min:
                min=z
            vColor.append([0,i.co.z,0])
        for i in vColor:
            i[2]=i[2]/(max-min)
        
        vertexColor=self.me.vertex_colors.new().data
        i2=0
        
        #these are the rgb values for certain 'biomes'
        #TODO:convert the color scheme to hex codes
        cWater=[0.004197,0,0.173]
        cSand=[0.711,0.659,0.119]
        cGrass=[0,0.376,0]
        cStone=[0.2,0.2,0.2]
        cSnow=[0.8,0.8,0.8]
        
        cChart=[[1,0.5,0.5]]*1000
        #for i in range(0,1000):
        #cChart[i]=[0.5,0.5,0.5]
        
        def mixCol(cArray,start,end):
            '''this function is for adding biome colors to the color 
            chart and blending them at the intersections'''
            for i in range(start,end):
                #the i value here represents the altitude
                #start and end are the beginning and end altitudes for each biome
                
                fac=1#this is the weight value for averaging the two biomes
                #if (i+20)>end:
                #    fac=0.5*((end-i)/20)**1.5
                #if (start+20)>i:
                #    fac=0.5*((i-start)/20)**1.5
                    
                #for j in range(0,3):
                #    cChart[i][j]=(1-fac)*cChart[i][j]+fac*cArray[j]
                #mag=0.5*sqrt(cChart[i][0]**2+cChart[i][1]**2+cChart[i][2]**2)
                cChart[i]=cArray
                #for j in range(0,3):
                #   cChart[i][j]=cArray[j]#0.5*cChart[i][j]/mag
            
        
        mixCol(cWater,0,250)
        mixCol(cSand,240,400)
        mixCol(cGrass,300,600)
        mixCol(cStone,500,850)
        mixCol(cSnow,800,1000)
        print(cChart[200])
        
        for poly in self.me.polygons:
            for idx in poly.loop_indices:
                loop=self.me.loops[idx]
                ver=loop.vertex_index
                [x,y,z]=self.me.vertices[ver].co
                z=(z-min)/(max-min)
                z=int(floor(z*1000)-1)
                #print(z)
                [r,g,b]=cChart[z]
                vertexColor[i2].color=[r,g,b]
                i2+=1
        #bpy.ops.object.mode_set(mode='VERTEX_PAINT')        
        self.mat.use_nodes=True
        node=self.mat.node_tree.nodes.new('ShaderNodeAttribute')
        node.attribute_name='Col'
        diff=self.mat.node_tree.nodes['Diffuse BSDF']
        self.mat.node_tree.links.new(node.outputs['Color'],diff.inputs['Color'])

    
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
    ter=Terrain("test")
    ter.genMesh()
    av=statistics.mean(noizArray)
    print('the average of noiz1 is: {}'.format(av))
    print('stdev is: {}'.format(statistics.stdev(noizArray)))
    ter.assignColors()
    
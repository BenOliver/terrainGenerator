import os
import sys
import bpy
import bmesh
import time
import statistics
import hashlib
from math import *
from mathutils import *
from random import random
import copy
C=bpy.context
D=bpy.data
M=D.meshes
O=D.objects


def myHash(*args):
	'''This function returns an 8 digit hex string
	using the md5 digest of objects passed to it
	it currently only supports ints,floats, and strings (or lists/tuples thereof)
	'''
	md5=hashlib.md5()
	if len(args)==0:
		#create random number if no arguments are passed
		args=[random()*1000]
	for entry in args:
		if isinstance(entry,int) | isinstance(entry,float):
			#turn number into binary format
			a=bin(int(entry)).encode()
			#md5 entries are concatenated together before digesting
			md5.update(a)
		elif isinstance(entry,str):
			#turn string into binary format
			a=entry.encode()
			md5.update(a)
	dig=md5.hexdigest()[:8]
	return int(dig,16),dig
		

class Terrain:
	'''an object which represents a landscape heightmap and uses blender for model creation and rendering.'''
	
	def __init__(self, name,seed=None):
		l('init started')
		self.tesselate=True
		self.origin=[0,0,0]
		self.name=name
		self.array=[]
		self.meshes={}
		self.ob=None
		self.detail=0
		self.arrSize=1
		self.roughness=1
		self.roughFactor=1
		
		if seed is None:
			#create random  hex string
			_,seed=myHashhex()
		
		self.originalSeed=seed
		
		#set a temporary worldSeed to enable fudgeOperator
		self.worldSeed,_=myHash(seed)		
		salt=self.fudge(1991,10,21)
		
		#create a new world seed using the fudge salt.
		#this is to identify any map changes which will occur if the fudge function is altered.
		self.worldSeed,self.worldSeedHex=myHash(salt,seed)		
		
		#write seeds to log file
		l('-'*20,flush=False)
		l('originalSeed:{}\nworldSeed:{}\nworldSeedHex:{}'.format(\
		self.originalSeed,self.worldSeed,self.worldSeedHex),flush=False)
		l('-'*20)
	
	def autoBuild(self,detail,painted=True):
		#construct and link, heightmap, mesh and material
		if isinstance(detail, tuple) | isinstance(detail,list) | isinstance(detail,range):
			#create heightmap
			self.genArray(detail=max(detail))
			for det in detail:
				#create the meshes of various detail
				m=self.createMesh(det)
				self.meshes[det]=m
				#create material for each mesh
				self.createMaterial(m,painted=painted)
		else:
			#if there is only one detail level given, do the same for single item.
			self.genArray(detail=detail)
			m=self.createMesh(detail=detail,xyScale=1,zAmp=1)
			self.meshes[detail]=m
			self.createMaterial(m,painted=painted)
		self.ob=self.createObject(m)

	def createMesh(self,detail=1,xyScale=1,zAmp=1):

		#create mesh name - this includes the seed and detail level to identify and re-use
		meshName='_'.join([self.name,'Mesh',self.worldSeedHex,str(detail),str(xyScale),str(zAmp)])
		#create new mesh
		if meshName in M:
			l('mesh {} already exists. reusing'.format(meshName))
			return M[meshName]
		me=M.new(meshName)
		
		#create bmesh
		bm=bmesh.new()
		bm.from_mesh(me)
		V=bm.verts
		E=bm.edges
		F=bm.faces			
		
		#create temporary grid to aid in generating 
		meshSize=2**detail
		vt=[0]*(meshSize+1)
		for i, item in enumerate(vt):
			vt[i]=[0]*(meshSize+1)

		step=2**(self.detail-detail)
		l('detailLevel:{},step:{}'.format(detail,step))
		for I,i in enumerate(range(0,self.arrSize+1,step)):
			for J,j in enumerate(range(0,self.arrSize+1,step)):
				#iterate through x,y values and set the coordinates for the mexh
				x=i*xyScale/self.arrSize
				y=j*xyScale/self.arrSize
				z=zAmp*self.array[i][j]*zAmp/self.arrSize
				#create new vertices and map vertices to array vt
				vt[I][J]=V.new((x,y,z))

		for i in range(0,len(vt)-1):
			for j in range(0, len(vt[i])-1):
				#create the faces between the vertices
				F.new((vt[i][j],vt[i+1][j],vt[i+1][j+1],vt[i][j+1]))
		#save the bmesh to the mesh
		bm.to_mesh(me)
		return me
	
	def createObject(self,mesh,name=None):
		if self.ob is None:
			if name is None:
				name=self.name
			#cleanup older versions if they exist
			self.delObject(name)
			#create new object
			ob=O.new(name,mesh)
			#give object location and link to scene
			ob.location=self.origin
			ob['seed']=self.originalSeed
			C.scene.objects.link(ob)
		#else:
		#	ob.data=mesh
		return ob

	def createMaterial(self,mesh,name=None,painted=True):
		if name is None:
			name=mesh.name+'_Mat'
		if name in D.materials:
			mat=D.materials[name]
			l('FUNC:createMaterial(), creating new material called {}'.format(name))
		else:
			l('Creating new material')
			mat=D.materials.new(name)
			mat.use_vertex_color_paint=1
			mat.use_nodes=True
			node=mat.node_tree.nodes.new('ShaderNodeAttribute')
			node.attribute_name='Col'
			diff=mat.node_tree.nodes['Diffuse BSDF']
			self.assignColors(mesh,mat)
		if name not in mesh.materials:
			mesh.materials.append(mat)
		if painted:
			mat.node_tree.links.new(mat.node_tree.nodes['Attribute']\
			.outputs['Color'],mat.node_tree.nodes['Diffuse BSDF'].inputs['Color'])
		return mat

	def genArray(self,roughness=1, roughFactor=1,detail=7):
		'''
		this function creates an array for terrain generation.
		best practice is to generate the highest detail required,
		and then use that array to create less detailed meshes
		'''
		self.detail=detail
		l('FUNC:genArray(), detail:{}'.format(self.detail))
		self.roughness=roughness      	#changes the baseline 'Roughess' TODO:change name
		self.roughFactor=roughFactor 	#changes how strong the roughness is (sensitive-keep around 1.0)
		self.arrSize=2**detail			#set level of detail. exponentially sensitive. 
										#values greater than 2**7 take longer than 1 second to compute
				
		#create the square grid of arrSize x arrSize squares
		v=[None]*(self.arrSize+1)
		for i, item in enumerate(v):
			v[i]=[None]*(self.arrSize+1)
			
		#initialize initial corner vertices
		v[0][0]=0
		v[0][-1]=0
		v[-1][0]=0
		v[-1][-1]=0
		
		r=int(self.arrSize/2)
		numSquares=self.arrSize/(2*r)
		#start with the original square and progress to smaller squares until at the smallest.
		#uses diamond square algorithm to generate new height values  
				
		while r>=1:
			#r is 'radius'
			if 2*r==self.arrSize:
				div=3
			else:
				div=4
				
			#diamond step
			for y in range(r, self.arrSize, 2*r):
				for x in range(r, self.arrSize, 2*r):
					v[x][y]=self.diamond(v,x,y,r)

			#square step					
			for y in range(0, self.arrSize+1, r):
				if y%(2*r)==0:
					start=r
				else:
					start=0
				#print('y is {}.\nstarting at {}'.format(y,start))
				for x in range(start, self.arrSize+1, 2*r):
					v[x][y]=self.square(v,x,y,r)
			
			r=int(r/2)
		#end of mesh generation
		self.array=v
				
	def assignColors(self,me,mat):
		#save z points to array, calculate max and min heights
		zVals=[i.co.z for i in me.vertices]
		maxZ=max(zVals)
		minZ=min(zVals)
		del(zVals)
		
		vertexColor=me.vertex_colors.new('Col').data
		#vertexColor2=self.me.vertex_colors.new('Col2').data
		
		#these are the rgb values for certain 'biomes'
		#TODO:convert the color scheme to hex codes
		biomes={}
		biomes['Water']={'startAlt':0,'endAlt':250,'rgb':Vector([0.004197,0,0.173])}
		biomes['Sand']={'startAlt':240,'endAlt':300,'rgb':Vector([0.711,0.659,0.119])}
		biomes['Grass']={'startAlt':300,'endAlt':700,'rgb':Vector([0,0.376,0])}
		biomes['Stone']={'startAlt':650,'endAlt':850,'rgb':Vector([0.2,0.2,0.2])}
		biomes['Snow']={'startAlt':800,'endAlt':1000,'rgb':Vector([0.8,0.8,0.8])}
		
		chartLen=1000
		colorChart=[None]*chartLen

		#this loop is for adding biome colors to the color\
		#chart and blending them at the intersections
		for name,biome in biomes.items():
			for i in range(biome['startAlt'],biome['endAlt']):
				if colorChart[i] is None:
					colorChart[i]=biome['rgb']
				else:
					colorChart[i]=0.2*colorChart[i]+0.8*biome['rgb']
						
		i2=0	#init index =0
		for poly in me.polygons:
			for idx in poly.loop_indices:
				#paint all the vertices in loop
				loop=me.loops[idx]
				ver=me.vertices[loop.vertex_index]
				[x,y,z]=ver.co
				if (maxZ-minZ):	#check if heightRange is non-0
					z=(z-minZ)/(maxZ-minZ)	#scale the z coord between max and min
				z=int(floor(z*chartLen)-1)
				[r,g,b]=colorChart[z]
				vertexColor[i2].color=[r,g,b]
				i2+=1
		
	def delMesh(self,delTarget):
		if delTarget in M:
			#if the mesh exists, unlink and delete it
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
			
	def fudge(self,x,y,r):
			#TODO: replace with standard library random generator
			seed1=self.worldSeed
			seed2=5
			prime1=96002369
			prime2=15646879
			prime3=10007
			#use the primes and world seed (worldSeed) to generate a pseudo-random number based on the x and y coordinates.
			#noiz is between 0 and 1.
			noiz=(((prime1*x/self.arrSize+prime2*y/self.arrSize+seed1)**seed2)%prime3)/prime3
			
			return self.roughness*(r**self.roughFactor)*(noiz-0.5)
		
	def diamond(self,matrix, x, y, r):
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
		v=(a+b+c+d)/4+self.fudge(x,y,r)

		return v
	
	def square(self,matrix, x, y, r):
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
			xSeed=x%self.arrSize
			ySeed=y%self.arrSize
			xNeg=(x-r)%self.arrSize
			xPos=(x+r)%self.arrSize
			yNeg=(y-r)%self.arrSize
			yPos=(y+r)%self.arrSize
			
			a=matrix[x][yNeg]
			b=matrix[xNeg][y]   			 
			c=matrix[xPos][y]
			d=matrix[x][yPos]
		else:
			xSeed=x
			ySeed=y
			xNeg=(x-r)
			xPos=(x+r)
			yNeg=(y-r)
			yPos=(y+r)
					 
			if 0<y<self.arrSize:
				a=matrix[x][yNeg]
				d=matrix[x][yPos]
			elif y==0:
				a=0
				d=matrix[x][yPos]
				div=3
			elif y==self.arrSize:
				a=matrix[x][yNeg]
				d=0
				div=3
				
			if 0<x<self.arrSize:
				b=matrix[xNeg][y]
				c=matrix[xPos][y]
			elif x==0:
				b=0
				c=matrix[xPos][y]
				div=3
			elif x==self.arrSize:
				b=matrix[xNeg][y]
				c=0
				div=3			
		v=(a+b+c+d)/div+self.fudge(xSeed,ySeed,r)
		return v

def main():
		
	logName='debugLog.log'
	lg=open(os.path.join(os.path.dirname(bpy.data.filepath),logName),'a+')
	global l
	def l(*args,flush=True):
		'''function writes strings to the debug log file
		'''
		for a in args:
			lg.write('\n'+str(a))
		if flush:
			lg.flush()
			
	lg.write('\n================================================='+\
	'\nDebug file for terrainGenerator')
	l(time.ctime())
	if 1:
	#clear old meshes and materials
		for m in D.meshes:
			m.user_clear()
			D.meshes.remove(m)
		for Mat in D.materials:
			Mat.user_clear()
			D.materials.remove(Mat)
	

	if 0:
		det=9
		ter=Terrain("test",seed="piningForTheFjords")
		painted=True
		ter.autoBuild(range(det),painted=painted)
		S=bpy.data.scenes['Scene']
		for i in range(det):
			ter.ob.data=ter.meshes[i]
			p='//seed_'+ter.originalSeed+'_detail_'+str(i)+('p' if painted else '')+'.png'
			S.render.stamp_note_text=p
			S.render.filepath='//renders'+p
			bpy.ops.render.render(write_still=True)
	else:
		ter=Terrain("test",seed='piningForTheFjords')
		#ter.tesselate=False
		ter.autoBuild(8)
		

	l('End of script\n\n')
	#close the log file
	lg.close()

if __name__ == '__main__':
	main()
		
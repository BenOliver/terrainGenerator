import os
import bpy
import bmesh
import time
import statistics
from math import *
from mathutils import *
from random import random
import copy
C=bpy.context
D=bpy.data
M=D.meshes
O=D.objects


class Terrain:
	'''a blender object which represents a landscape heightmap'''
	global log
	
	Dbug=False  		#for debugging. value of 1 to print logs
	def __init__(self, name,seed=None):
		l('init started')
		self.tesselate=True
		self.origin=[0,0,0]
		self.name=name
		self.array=[]
		self.meshes={}
		self.ob=None
		self.detail=0
		if seed is None:
			#create random  hex string
			seed=hex(hash(random())%(2**32))[2:] #remove the 0x prefix
		self.originalSeed=seed
		self.worldSeed=hash(self.originalSeed)%(2**32)
		self.worldSeedHex=hex(self.worldSeed)[2:] 
	
	def autoBuild(self,detail,painted=True):
		if isinstance(detail, tuple) | isinstance(detail,list) | isinstance(detail,range):
			self.genMesh(detail=max(detail))
			for det in detail:
				m=self.createMesh(det)
				self.meshes[det]=m
				self.createMaterial(m,painted=painted)
		else:
			self.genMesh(detail=detail)
			m=self.createMesh(detail=detail)
			self.meshes[detail]=m
			self.createMaterial(m,painted=painted)
		self.ob=self.createObject(m)

	def createMesh(self,detail=1,xyScale=1,zAmp=1):

		#create mesh name - this includes the seed and detail level to identify and re-use
		meshName='_'.join([self.name,'Mesh',self.worldSeedHex,str(detail)])
		#create new mesh
		if meshName in M:
			return M[meshName]
			#self.delMesh(meshName)
		me=M.new(meshName)
		#self.meshes[detail]=self.genMesh(me,terDetail=detail)
		
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
		
#		vt[0][0]=0
#		vt[0][-1]=0
#		vt[-1][0]=0
#		vt[-1][-1]=0
		step=2**(self.detail-detail)
		l('detailLevel:{},step:{}'.format(detail,step))
		for I,i in enumerate(range(0,self.arrSize+1,step)):
			for J,j in enumerate(range(0,self.arrSize+1,step)):
				x=i*xyScale/self.arrSize
				y=j*xyScale/self.arrSize
				z=zAmp*self.array[i][j]*zAmp/self.arrSize
				vt[I][J]=V.new((x,y,z))

		for i in range(0,len(vt)-1):
			for j in range(0, len(vt[i])-1):
				#create the faces between the vertices
				F.new((vt[i][j],vt[i+1][j],vt[i+1][j+1],vt[i][j+1]))
		
		bm.to_mesh(me)
		return me
		
		
		
		
		
		
		return self.meshes[detail]
	
	def createObject(self,mesh,name=None):
		if self.ob is None:
			if name is None:
				name=self.name
			#print('1: {}'.format(name2))
			#print('2:{}'.format(name3))
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
			self.delMaterial(name)
		mat=D.materials.new(name)
		mesh.materials.append(mat)
		mat.use_vertex_color_paint=1
		mat.use_nodes=True
		node=mat.node_tree.nodes.new('ShaderNodeAttribute')
		node.attribute_name='Col'
		diff=mat.node_tree.nodes['Diffuse BSDF']
		self.assignColors(mesh,mat)
		if painted:
			mat.node_tree.links.new(node.outputs['Color'],diff.inputs['Color'])
		return mat


	def dprint(*args):
		if Terrain.Dbug==True:
			print(args)

	def genMesh(self,roughness=1, roughFactor=1,detail=7):
		'''
		this function creates an array for terrain generation.
		best practice is to generate the highest detail required,
		and then use that array to create less detailed meshes
		'''
		self.detail=detail
		l('generating mesh of detail:{}'.format(self.detail))
		self.roughness=roughness      	#changes the baseline 'Roughess' TODO:change name
		self.roughFactor=roughFactor 	#changes how strong the roughness is (sensitive-keep around 1.0)
		self.arrSize=2**detail			#set level of detail. exponentially sensitive. 
											#values greater than 2**7 take longer than 1 second to compute
				
		#create the square grid of arrSize x arrSize squares
		v=[None]*(self.arrSize+1)
		for i, item in enumerate(v):
			v[i]=[None]*(self.arrSize+1)
		#v=[[None]*(self.arrSize+1)]*(self.arrSize+1)

			
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
		self.array=v
		#end of mesh generation

		
					
	def assignColors(self,me,mat):
		vColor=[]
		maxZ=0
		minZ=0
		
		#save z points to array, calculate max and min heights
		for i in me.vertices:
			z=i.co.z
			if z>maxZ:
				maxZ=z
			if z<minZ:
				minZ=z
			vColor.append([0,i.co.z,0])
		for i in vColor:
			if (maxZ-minZ):
				i[2]=i[2]/(maxZ-minZ)
		
		vertexColor=me.vertex_colors.new('Col').data
		#vertexColor2=self.me.vertex_colors.new('Col2').data
		
		#these are the rgb values for certain 'biomes'
		#TODO:convert the color scheme to hex codes
		biomes={}
		biomes['Water']={'startAlt':0,'endAlt':250,'rgb':Vector([0.004197,0,0.173])}
		biomes['Sand']={'startAlt':240,'endAlt':400,'rgb':Vector([0.711,0.659,0.119])}
		biomes['Grass']={'startAlt':300,'endAlt':600,'rgb':Vector([0,0.376,0])}
		biomes['Stone']={'startAlt':500,'endAlt':850,'rgb':Vector([0.2,0.2,0.2])}
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
						


		i2=0
		for poly in me.polygons:
			for idx in poly.loop_indices:
				loop=me.loops[idx]
				ver=me.vertices[loop.vertex_index]
				[x,y,z]=ver.co
				if (maxZ-minZ):
					z=(z-minZ)/(maxZ-minZ)
				z=int(floor(z*chartLen)-1)
				#print(z)
				[r,g,b]=colorChart[z]
				vertexColor[i2].color=[r,g,b]
				#vertexColor2[i2].color=colorChart2[z]
				i2+=1
		#bpy.ops.object.mode_set(mode='VERTEX_PAINT)
		



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
			#noiz=(((prime1*x*self.terrScale/self.arrSize+prime2*y*self.terrScale/self.arrSize+seed1)**seed2)%prime3)/prime3
			noiz=(((prime1*x/self.arrSize+prime2*y/self.arrSize+seed1)**seed2)%prime3)/prime3
			return self.roughness*(r**self.roughFactor)*(noiz-0.5)
			#the -0.5 balances the heighmap around the midplane
		
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
		

		
if __name__ == '__main__':

	logName='debugLog.txt'
	lg=open(os.path.join(os.path.dirname(bpy.data.filepath),logName),'w+')
	def l(*args,flush=True):
		'''function writes strings to the debug file
		'''
		for a in args:
			lg.write('\n'+str(a))
		if flush:
			lg.flush()
			
	lg.write('Debug file for terrainGenerator')
	l(time.ctime())
	for m in D.meshes:
		m.user_clear()
		D.meshes.remove(m)
	

	if 0:
		det=9
		ter=Terrain("test",seed="piningForTheFjords")
		#for mesh in M:
		#	ter.delMesh(mesh.name) # clear old meshes out
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
		ter=Terrain("test",seed="piningForTheFjords")
		ter.autoBuild(11)
		

	l('End of script')
	lg.close()

#Terrain Generator
This script is for generating realistic looking heightmaps and creating blender meshes using blender's python interface.

This is just a fun project of mine that I decided to upload to get to grips with using git. Most of this code is a few years old, and I'll try and update it when possible, but I'm not expecting it to see much use by others.

The main technique used in generating the heightmap is the [Diamond-square algorithm](https://en.wikipedia.org/wiki/Diamond-square_algorithm).
The random element in the generation is pseudo-random and calculated using the x and y coordinates plus a world-seed. This allows generation of the same landscape using only the world seed. This also allows for adaptive refinement of detail.
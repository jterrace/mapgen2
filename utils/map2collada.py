#!/usr/bin/env python

import sys
import os.path
from xml.etree import ElementTree as etree
from optparse import OptionParser

X_SCALE = 1.0
Y_SCALE = 1.0
Z_SCALE = 100.0

COLORS = {
    # Features
    'OCEAN': 0x44447a,
    'COAST': 0x33335a,
    'LAKESHORE': 0x225588,
    'LAKE': 0x336699,
    'RIVER': 0x225588,
    'MARSH': 0x2f6666,
    'ICE': 0x99ffff,
    'BEACH': 0xa09077,
    'ROAD1': 0x442211,
    'ROAD2': 0x553322,
    'ROAD3': 0x664433,
    'BRIDGE': 0x686860,
    'LAVA': 0xcc3333,
    
    # Terrain
    'SNOW': 0xffffff,
    'TUNDRA': 0xbbbbaa,
    'BARE': 0x888888,
    'SCORCHED': 0x555555,
    'TAIGA': 0x99aa77,
    'SHRUBLAND': 0x889977,
    'TEMPERATE_DESERT': 0xc9d29b,
    'TEMPERATE_RAIN_FOREST': 0x448855,
    'TEMPERATE_DECIDUOUS_FOREST': 0x679459,
    'GRASSLAND': 0x88aa55,
    'SUBTROPICAL_DESERT': 0xd2b98b,
    'TROPICAL_RAIN_FOREST': 0x337755,
    'TROPICAL_SEASONAL_FOREST': 0x559944
}

def hex2rgb(i):
    b = i & 255
    g = (i >> 8) & 255
    r = (i >> 16) & 255
    return (r / 255.0, g / 255.0, b / 255.0)

class MapObject(object):
    def __init__(self, elem):
        self.elem = elem
        
        for prop in self.PROPS:
            setattr(self, prop, elem.get(prop))
            
        for prop in self.NUMERICS:
            setattr(self, prop, float(getattr(self, prop)))
            
        for prop in self.BOOLEANS:
            setattr(self, prop, True if getattr(self, prop) == 'true' else False)

class Center(MapObject):
    PROPS = ['biome', 'elevation', 'coast', 'water', 'moisture', 'y', 'x', 'ocean', 'border', 'id']
    NUMERICS = ['x', 'y', 'elevation', 'moisture']
    BOOLEANS = ['water', 'coast', 'ocean', 'border']
            
    def add_pointers(self, corners, edges):
        self.corners = []
        for corner_elem in self.elem.findall('corner'):
            corner_id = corner_elem.get('id')
            self.corners.append(corners[corner_id])
            
        self.edges = []
        for edge_elem in self.elem.findall('edge'):
            edge_id = edge_elem.get('id')
            self.edges.append(edges[edge_id])
    
    def __str__(self):
        return "<Center id=%s (%.7g, %.7g, %.7g)>" % (self.id, self.x, self.y, self.elevation)
    def __repr__(self):
        return str(self)

class Corner(MapObject):
    PROPS = ['water', 'elevation', 'coast', 'downslope', 'moisture', 'ocean', 'y', 'x', 'river', 'border', 'id']
    NUMERICS = ['x', 'y', 'elevation', 'moisture', 'downslope', 'river']
    BOOLEANS = ['water', 'coast', 'ocean', 'border']
            
    def __str__(self):
        return "<Corner id=%s (%.7g, %.7g, %.7g)>" % (self.id, self.x, self.y, self.elevation)
    def __repr__(self):
        return str(self)
    
class Edge(object):
    def __init__(self, elem, corners, centers):
        self.elem = elem
        
        corner0 = elem.get('corner0')
        corner1 = elem.get('corner1')
        self.corner0 = corners.get(corner0)
        self.corner1 = corners.get(corner1)
        
        center0 = elem.get('center0')
        center1 = elem.get('center1')
        self.center0 = centers.get(center0)
        self.center1 = centers.get(center1)
        
        self.x = elem.get('x')
        self.y = elem.get('y')
        self.x = float(self.x) if self.x is not None else None
        self.y = float(self.y) if self.y is not None else None
        
        self.id = elem.get('id')
    
def visualize(centers, corners, edges):
    from meshtool.filters.panda_filters.pandacore import getVertexData, attachLights, ensureCameraAt
    from meshtool.filters.panda_filters.pandacontrols import KeyboardMovement, MouseDrag, MouseScaleZoom
    from panda3d.core import GeomPoints, GeomTriangles, Geom, GeomNode, GeomVertexFormat, GeomVertexData, GeomVertexWriter, LineSegs
    from direct.showbase.ShowBase import ShowBase
    
    format = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData('pts', format, Geom.UHDynamic)
    vertex = GeomVertexWriter(vdata, 'vertex')
    color = GeomVertexWriter(vdata, 'color')
    
    vertex_index = 0
    center_vertex_indices = {}
    corner_vertex_indices = {}
    for key, center in centers.iteritems():
        vertex.addData3f(center.x * X_SCALE, center.y * Y_SCALE, center.elevation * Z_SCALE)
        curcolor = hex2rgb(COLORS[center.biome])
        color.addData4f(curcolor[0], curcolor[1], curcolor[2], 1)
        center_vertex_indices[key] = vertex_index
        vertex_index += 1
        
        for corner in center.corners:
            vertex.addData3f(corner.x * X_SCALE, corner.y * Y_SCALE, corner.elevation * Z_SCALE)
            color.addData4f(curcolor[0], curcolor[1], curcolor[2], 1)
            corner_vertex_indices[corner.id] = vertex_index
            vertex_index += 1
    
    tris = GeomTriangles(Geom.UHDynamic)
    
    for edge in edges.itervalues():
        corner0 = edge.corner0
        corner1 = edge.corner1
        center0 = edge.center0
        center1 = edge.center1
        if corner0 is None or corner1 is None:
            continue
        
        tris.addVertices(corner_vertex_indices[corner1.id],
                         corner_vertex_indices[corner0.id],
                         center_vertex_indices[center0.id])
        
        tris.addVertices(center_vertex_indices[center1.id],
                         corner_vertex_indices[corner0.id],
                         corner_vertex_indices[corner1.id])
        
    
    tris.closePrimitive()

    pgeom = Geom(vdata)
    pgeom.addPrimitive(tris)

    node = GeomNode("primitive")
    node.addGeom(pgeom)

    p3dApp = ShowBase()
    attachLights(render)
    geomPath = render.attachNewNode(node)
    #geomPath.setRenderModeThickness(6.0)
    
    #geomPath.setRenderModeWireframe()
    
    ensureCameraAt(geomPath, base.cam)
    
    boundingSphere = geomPath.getBounds()
    base.cam.setPos(boundingSphere.getCenter() + boundingSphere.getRadius())

    base.cam.lookAt(boundingSphere.getCenter())
    
    KeyboardMovement()
    MouseDrag(geomPath)
    MouseScaleZoom(geomPath)
    #render.setShaderAuto()
    p3dApp.run()

def tocollada(centers, corners, edges):
    import collada
    import numpy
    
    mesh = collada.Collada()
    biome_materials = {}
    biome_triangles = {}
    for name, diffuse_value in COLORS.iteritems():
        effect = collada.material.Effect("effect-" + name, [], "phong", diffuse=hex2rgb(diffuse_value))
        mesh.effects.append(effect)
        mat = collada.material.Material("material-" + name, "material-" + name, effect)
        mesh.materials.append(mat)
        biome_materials[name] = mat
        biome_triangles[name] = []
    
    vertex = []
    vertex_index = 0
    center_vertex_indices = {}
    corner_vertex_indices = {}
    for key, center in centers.iteritems():
        vertex.append([center.x * X_SCALE, center.y * Y_SCALE, center.elevation * Z_SCALE])
        center_vertex_indices[key] = vertex_index
        vertex_index += 1
        
        for corner in center.corners:
            vertex.append([corner.x * X_SCALE, corner.y * Y_SCALE, corner.elevation * Z_SCALE])
            corner_vertex_indices[corner.id] = vertex_index
            vertex_index += 1
            
        for edge in center.edges:
            corner0 = edge.corner0
            corner1 = edge.corner1
            center0 = edge.center0
            center1 = edge.center1
            if corner0 is None or corner1 is None:
                continue
            
            if key == center0.id:
                newtri = [corner_vertex_indices[corner1.id],
                          corner_vertex_indices[corner0.id],
                          center_vertex_indices[center0.id]]
            
            elif key == center1.id:
                newtri = [center_vertex_indices[center1.id],
                          corner_vertex_indices[corner0.id],
                          corner_vertex_indices[corner1.id]]
                
            biome_triangles[center.biome].append(newtri)
    
    vert_src = collada.source.FloatSource("terrain-verts-array", numpy.array(vertex, dtype=numpy.float32), ('X', 'Y', 'Z'))
    geom = collada.geometry.Geometry(mesh, "terrain-geometry", "terrain-geometry", [vert_src])
    input_list = collada.source.InputList()
    input_list.addInput(0, 'VERTEX', "#terrain-verts-array")
    
    matnodes = []
    for biome_name in COLORS.iterkeys():
        biome_material = biome_materials[biome_name]
        biome_indices = numpy.array(biome_triangles[biome_name], dtype=numpy.int32)
        
        triset = geom.createTriangleSet(biome_indices, input_list, biome_material.id)
        geom.primitives.append(triset)
        
        matnode = collada.scene.MaterialNode(biome_material.id, biome_material, inputs=[])
        matnodes.append(matnode)
    
    mesh.geometries.append(geom)
    geomnode = collada.scene.GeometryNode(geom, matnodes)
    node = collada.scene.Node("node0", children=[geomnode])
    scene = collada.scene.Scene("scene0", [node])
    mesh.scenes.append(scene)
    mesh.scene = scene
    mesh.assetInfo.upaxis = collada.asset.UP_AXIS.Z_UP
    
    return mesh

def main():
    parser = OptionParser(usage="Usage: map2collada.py -o file.dae map.xml",
                          description="Converts mapgen2 XML file to COLLADA using pycollada")
    parser.add_option("-o", "--outfile", dest="outfile",
                      help="write DAE to FILE", metavar="OUTFILE")
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.print_help()
        parser.exit(1, "Wrong number of arguments.\n")
    
    if not os.path.isfile(args[0]):
        parser.print_help()
        parser.exit(1, "Input file '%s' is not a valid file.\n" % args[0])
    
    if options.outfile is None:
        parser.print_help()
        parser.exit(1, "Must specify an output file.\n")
        
    fname = args[0]
    
    e = etree.parse(fname)
    
    generator = e.find("generator")
    generated_url = generator.get('url')
    time_generated = generator.get('timestamp')
    sys.stdout.write("Generated map file created on '%s' via URL '%s'.\n" % (time_generated, generated_url))
    
    center_elems = e.find("centers")
    corner_elems = e.find("corners")
    edge_elems = e.find("edges")
    sys.stdout.write("Found %d centers.\n" % len(center_elems))
    sys.stdout.write("Found %d corners.\n" % len(corner_elems))
    sys.stdout.write("Found %d edges.\n" % len(edge_elems))
    
    centers = {}
    for center_elem in center_elems:
        center = Center(center_elem)
        centers[center.id] = center
    
    corners = {}
    for corner_elem in corner_elems:
        corner = Corner(corner_elem)
        corners[corner.id] = corner
        
    edges = {}
    for edge_elem in edge_elems:
        edge = Edge(edge_elem, corners, centers)
        edges[edge.id] = edge
        
    for center in centers.itervalues():
        center.add_pointers(corners, edges)
    
    #visualize(centers, corners, edges)
    dae = tocollada(centers, corners, edges)
    dae.write(options.outfile)

if __name__ == '__main__':
    main()

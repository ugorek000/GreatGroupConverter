bl_info = {'name':"GreatGroupConverter", 'author':"ugorek", 'version':(9,9,9), 'blender':(4,0,2), #2023.12.13
           'description':"", 'location':"N Panel > *select group* > Misc",
           'warning':"Non-zero chance of crash in unexplored exceptions", 'category':"Node",
           'wiki_url':"https://github.com/ugorek000/GreatGroupConverter/wiki", 'tracker_url':"https://github.com/ugorek000/GreatGroupConverter/issues"}
addonName = bl_info['name']

from builtins import len as length
import bpy, re
import mathutils

list_classes = []

set_ignoredNdProps = {'node_tree', 'bl_idname'} #На счёт второго не знаю.
def FullCopyNode(fromNd, toNd):
    for pr in fromNd.bl_rna.properties:
        if (not pr.is_readonly)and(pr.identifier not in set_ignoredNdProps):
            try: #Для разных нод между Shader и Texture с одинаковым названием; например ShaderNodeTexNoise.
                setattr(toNd, pr.identifier, getattr(fromNd, pr.identifier))
            except:
                pass
            #Заметка: теперь где-то естественным образом обрабатывается NoiseTexture между ShaderNodeEditor и TextureNodeEditor.
    if hasattr(fromNd,'color_ramp'):
        for pr in fromNd.color_ramp.bl_rna.properties:
            if not pr.is_readonly:
                setattr(toNd.color_ramp, pr.identifier, getattr(fromNd.color_ramp, pr.identifier))
        for cyc in range(length(fromNd.color_ramp.elements)-2):
            toNd.color_ramp.elements.new(0.0)
        for cyc in range(length(fromNd.color_ramp.elements)):
            toNd.color_ramp.elements[cyc].position = fromNd.color_ramp.elements[cyc].position
            toNd.color_ramp.elements[cyc].color =    fromNd.color_ramp.elements[cyc].color
    if hasattr(fromNd,'mapping'):
        for pr in fromNd.mapping.bl_rna.properties:
            if not pr.is_readonly:
                setattr(toNd.mapping, pr.identifier, getattr(fromNd.mapping, pr.identifier))
        for cyc1 in range(length(fromNd.mapping.curves)):
            for cyc2 in range(length(fromNd.mapping.curves[cyc1].points)-2):
                toNd.mapping.curves[cyc1].points.new(0.0, 1.0)
            for cyc2 in range(length(fromNd.mapping.curves[cyc1].points)):
                toNd.mapping.curves[cyc1].points[cyc2].location =    fromNd.mapping.curves[cyc1].points[cyc2].location
                toNd.mapping.curves[cyc1].points[cyc2].handle_type = fromNd.mapping.curves[cyc1].points[cyc2].handle_type

class NodeFiller(bpy.types.Node):
    bl_idname = 'GgcNodeFiller'
    bl_label = "Node Filler"
    bl_width_max = 1024
    bl_width_min = 0
    blid: bpy.props.StringProperty(default="Ggc Node Filler")
    def draw_label(self):
        return self.blid
    def draw_buttons(self, context, layout):
        pass

list_classes += [NodeFiller]

import ctypes

class StructBase(ctypes.Structure):
    _subclasses = []
    __annotations__ = {}
    def __init_subclass__(cls):
        cls._subclasses.append(cls)
    def InitStructs():
        for cls in StructBase._subclasses:
            fields = []
            for field, value in cls.__annotations__.items():
                fields.append((field, value))
            if fields:
                cls._fields_ = fields
            cls.__annotations__.clear()
        StructBase._subclasses.clear()

class BNodeType(StructBase): #source\blender\blenkernel\BKE_node.h
    idname:         ctypes.c_char*64
    type:           ctypes.c_int
    ui_name:        ctypes.c_char*64
    ui_description: ctypes.c_char*256
    ui_icon:        ctypes.c_int
    if bpy.app.version>=(4,0,0):
        char:           ctypes.c_void_p
    width:          ctypes.c_float
    minwidth:       ctypes.c_float
    maxwidth:       ctypes.c_float
    height:         ctypes.c_float
    minheight:      ctypes.c_float
    maxheight:      ctypes.c_float
    nclass:         ctypes.c_int16 #github.com/ugorek000/ManagersNodeTree

class BNode(StructBase): #source\blender\makesdna\DNA_node_types.h:
    next:       ctypes.c_void_p
    prev:       ctypes.c_void_p
    inputs:     ctypes.c_void_p*2
    outputs:    ctypes.c_void_p*2
    name:       ctypes.c_char*64
    identifier: ctypes.c_int
    flag:       ctypes.c_int
    idname:     ctypes.c_char*64
    typeinfo:   ctypes.POINTER(BNodeType)
    type:       ctypes.c_int16
    ui_order:   ctypes.c_int16
    custom1:    ctypes.c_int16
    custom2:    ctypes.c_int16
    custom3:    ctypes.c_float
    custom4:    ctypes.c_float
    id:         ctypes.c_void_p
    storage:    ctypes.c_void_p
    prop:       ctypes.c_void_p
    parent:     ctypes.c_void_p
    locx:       ctypes.c_float
    locy:       ctypes.c_float
    width:      ctypes.c_float
    height:     ctypes.c_float
    offsetx:    ctypes.c_float
    offsety:    ctypes.c_float
    label:      ctypes.c_char*64
    color:      ctypes.c_float*3
    @classmethod
    def get_fields(cls, so):
        return cls.from_address(so.as_pointer())

StructBase.InitStructs()

def GetSocketIndex(sk):
    return int(sk.path_from_id().split(".")[-1].split("[")[-1][:-1])

def RememberAllLinks(nameTar):
    list_allFoundLinks = []
    list_allFoundNodes = []
    def RememberLinks(tree, nameTar):
        for nd in tree.nodes:
            if (getattr(nd, 'node_tree', False))and(nd.node_tree.name==nameTar):
                for lk in tree.links:
                    if (lk.from_node==nd)or(lk.to_node==nd):
                        list_allFoundLinks.append( (lk.id_data,
                                                    lk.from_node.name, lk.from_socket.name, GetSocketIndex(lk.from_socket),
                                                    lk.to_node.name,   lk.to_socket.name,   GetSocketIndex(lk.to_socket)) )
                list_allFoundNodes.append( (nd, []) )
                for sk in nd.inputs:
                    if hasattr(sk, 'default_value'):
                        list_allFoundNodes[-1][1].append( (sk.name, sk.default_value[:] if sk.bl_rna.properties['default_value'].is_array else sk.default_value) )
    for ng in bpy.data.node_groups:
        RememberLinks(ng, nameTar)
    for si in {'materials', 'worlds', 'lights', 'linestyles', 'scenes', 'textures'}:
        for wh in getattr(bpy.data, si):
            if wh.node_tree:
                RememberLinks(wh.node_tree, nameTar)
    return list_allFoundLinks, list_allFoundNodes
def RestoreAllLinks(list_allFoundLinks, list_allFoundNodes): #Остерегаться одинаковых имён!
    for li in list_allFoundLinks:
        try: #По имени приоритетнее, потому что!
            li[0].links.new( li[0].nodes.get(li[1]).outputs.get(li[2]), li[0].nodes.get(li[4]).inputs.get(li[5]) )
        except:
            li[0].links.new( li[0].nodes.get(li[1]).outputs[li[3]],     li[0].nodes.get(li[4]).inputs[li[6]] )
    for li in list_allFoundNodes: #Восстановить содержимое не подсоединённых сокетов.
        for saved in li[1]:
            sk = li[0].inputs.get(saved[0])
            if sk:
                sk.default_value = saved[1]

set_ignoredSkProps = {'type', 'bl_idname'}
#Про 'bl_socket_idname' см.:
#projects.blender.org/blender/blender/issues/116082
#projects.blender.org/blender/blender/issues/116116
set_ignoredSkfProps = {'socket_type','bl_socket_idname'}
def InterfacesTransfer(treeFrom, treeTo):
    treeTo.interface.clear()
    for skfFrom in treeFrom.interface.items_tree:
        skfTo = treeTo.interface.new_socket(skfFrom.bl_socket_idname, in_out=skfFrom.in_out)
        err = None
        try:
            skfTo.socket_type = skfFrom.socket_type
        except:
            err = skfFrom.socket_type+" not found"
        for pr in skfFrom.bl_rna.properties:
            if (not pr.is_readonly)and(pr.identifier not in set_ignoredSkfProps):
                if pr.identifier in skfTo.bl_rna.properties: #Не знаю, только эстетика, или влияет на что.
                    txt = "."+pr.identifier
                    txt = repr(skfTo)+txt+" = "+repr(skfFrom)+txt
                    try: #Из-за 'NodeSocketString'; а также см. багрепорты выше.
                        exec(txt) #Легально устанавливать что-то не задалось; см. ниже.
                    except:
                        pass
                    #setattr(skfTo, pr.identifier, getattr(skfFrom, pr.identifier))
                    #range(min(pr.array_length, skfTo.bl_rna.properties[pr.identifier].array_length))
                    #if getattr(pr,'is_array', None): getattr(skfTo, pr.identifier)[cyc] = getattr(skfFrom, pr.identifier)[cyc] #Чёрная магия, оно не работает, красный в зелёный пишется и далее со сдвигом.
                    #Это как-то связано? `tree.interface.items_tree[0].bl_rna.properties['default_value'].array_dimensions[1]`?
        if err:
            skfTo.name = "⚠️ "+skfTo.name+" ‒ "+err.split("enum")[-1]
            skfTo.hide_value = True


set_quartetNames = {"Shader", "Geometry", "Compositor", "Texture"}
reQuartetPatt = "^("+"|".join(set_quartetNames)+")"
set_geoExceptions = {'NodeValToRGB','NodeMixRGB','NodeRGBCurve','NodeTexBrick','NodeTexChecker','NodeTexGradient','NodeTexMagic','NodeTexMusgrave',
        'NodeTexNoise','NodeTexVoronoi','NodeTexWave','NodeTexWhiteNoise','NodeClamp','NodeFloatCurve','NodeMapRange','NodeMath','NodeCombineXYZ',
        'NodeSeparateXYZ','NodeVectorCurve','NodeVectorMath','NodeVectorRotate','NodeValue'}
set_canonTrees = {'ShaderNodeTree', 'GeometryNodeTree'}
def MixThCol(col1, col2, fac=0.4): #/source/blender/editors/space_node/node_draw.cc  node_draw_basis()  /* Header. */
    return col1*(1-fac)+col2*fac
def NodesTransfer(treeFrom, treeTo):
    treeTo.nodes.clear()
    blidGroupFrom = treeFrom.bl_idname.replace("Tree","Group")
    blidGroupTo = treeTo.bl_idname.replace("Tree","Group")
    blidTo = treeTo.bl_idname
    blidRawTo = blidTo.replace("NodeTree","")
    neTheme = bpy.context.preferences.themes[0].node_editor
    colBg = mathutils.Color(neTheme.node_backdrop[:3])
    for ndFrom in treeFrom.nodes:
        try:
            ndTo = None
            txt = ndFrom.bl_idname
            if txt==blidGroupFrom:
                txt = blidGroupTo
            blidTrySame = re.sub(reQuartetPatt, blidRawTo, txt)
            if hasattr(bpy.types, blidTrySame):
                txt = blidTrySame
            blidRaw = re.sub(reQuartetPatt, "", txt)
            if (blidTo=='GeometryNodeTree')and(blidRaw in set_geoExceptions):
                txt = "Shader"+blidRaw
            if blidTo=='CompositorNodeTree':
                txt = {'ShaderNodeRGBCurve':'CompositorNodeCurveRGB', 'ShaderNodeVectorCurve':'CompositorNodeCurveVec'}.get(txt, txt)
            if blidTo=='ShaderNodeTree':
                txt = {'CompositorNodeCurveRGB':'ShaderNodeRGBCurve', 'CompositorNodeCurveVec':'ShaderNodeVectorCurve'}.get(txt, txt)
            ndTo = treeTo.nodes.new(txt)
            FullCopyNode(ndFrom, ndTo)
            if hasattr(ndTo,'node_tree'):
                ndTo.node_tree = RecrDoConvertNodeTree(ndFrom.node_tree, blidTo) #Заметка: и пораньше тоже можно, но тогда пришлось бы париться с annex.
            def TransferNodePuts(putsFrom, putsTo):
                for skFrom in putsFrom: #Заметка: перенос своих же NodeFiller.
                    #Заметка: по имени, а не по индексу. Например VectorCurve между Shader и Compositor различается фактором.
                    skTo = putsTo.get(skFrom.name)
                    if skTo:
                        for pr in skFrom.bl_rna.properties:
                            if (not pr.is_readonly)and(pr.identifier not in set_ignoredSkProps): #Здесь без set_ignoredSkProps вроде не крашится.
                                setattr(skTo, pr.identifier, getattr(skFrom, pr.identifier))
            if ndTo.bl_idname==NodeFiller.bl_idname:
                1/0 #В TransferNodePuts() теперь по имени, а не по индексу, так что всё ещё "не обломались".
            TransferNodePuts(ndFrom.inputs, ndTo.inputs)
            TransferNodePuts(ndFrom.outputs, ndTo.outputs)
        except Exception as ex:
            if ndTo: #Для своих NodeFiller, и в целом общее.
                treeTo.nodes.remove(ndTo)
            nd = treeTo.nodes.new(NodeFiller.bl_idname)
            nd.blid = ndFrom.bl_idname
            for put in {'inputs','outputs'}:
                putsTo = getattr(nd, put)
                for skFrom in getattr(ndFrom, put):
                    blid = skFrom.bl_idname
                    #blid = {'NodeSocketGeometry':'NodeSocketMaterial'}.get(blid, blid)
                    skTo = putsTo.new(blid, skFrom.name)
                    for pr in skFrom.bl_rna.properties:
                        if (not pr.is_readonly)and(pr.identifier not in set_ignoredSkProps):
                            setattr(skTo, pr.identifier, getattr(skFrom, pr.identifier))
            nd.location = ndFrom.location
            if ndFrom.bl_idname in set_omgApiNodesWidth: #-_-
                nd.width = BNode.get_fields(ndFrom).width
            else:
                nd.width = ndFrom.width
            nd.name = ndFrom.name
            nd.label = ndFrom.label if ndFrom.label else ndFrom.bl_label
            #nd.label = str(ex)
            nd.use_custom_color = True
            try: #Ох уж этот FunctionNodeInputColor.
                if ndFrom.bl_idname=='NodeUndefined':
                    nd.color = (0.633459, 0.226727, 0.226727)
                    nd.hide = True #!?
                else:
                    nd.color = MixThCol(colBg, neTheme.input_node)
            except:
                pass
set_omgApiNodesWidth = {'CompositorNodeBoxMask', 'CompositorNodeEllipseMask'}

def RecrDoConvertNodeTree(treeFrom, blidTo):
    nameTo = treeFrom.name
    prefs = Prefs()
    annex = prefs.suffixMain + getattr(prefs, *[li for li in {'suffixSh', 'suffixGm', 'suffixCp', 'suffixTx'} if li[6]==blidTo[0]])
    if not nameTo.endswith(annex):
        nameTo += annex
    treeTo = bpy.data.node_groups.get(nameTo) or bpy.data.node_groups.new(nameTo, blidTo)
    ##
    list_allFoundLinks, list_allFoundNodes = RememberAllLinks(nameTo)
    InterfacesTransfer(treeFrom, treeTo)
    RestoreAllLinks(list_allFoundLinks, list_allFoundNodes)
    ##
    NodesTransfer(treeFrom, treeTo)
    for lk in treeFrom.links: #Благодаря гениальной идеи кастомного нода, перенос линков сколлапсировался до 4-х строчек. Огонь!
        try:
            skOut = treeTo.nodes.get(lk.from_node.name).outputs[GetSocketIndex(lk.from_socket)]
            skIn = treeTo.nodes.get(lk.to_node.name).inputs[GetSocketIndex(lk.to_socket)]
            treeTo.links.new(skOut, skIn)
        except: #Так же, как и в FullCopyNode().
            pass
    ##
    for nd in treeTo.nodes:
        nd.select = False
    treeTo.nodes.active = None #Пользовательские "елозенья" от последующих конвертаций.
    return treeTo

def AddHighlightingText(where, *texts):
    rowMain = where.row(align=True)
    rowMain.alignment = 'LEFT'
    for cyc, txt in enumerate(texts):
        if txt:
            row = rowMain.row(align=True)
            row.alignment = 'CENTER'
            row.label(text=txt)
            row.active = cyc%2

list_lastConverts = []
lastConvertTree = None

set_gncNdPollTypeTarget = {'GROUP', 'GROUP_INPUT', 'GROUP_OUTPUT'}
def GetTargetConvert(tree):
    if tree:
        aNd = tree.nodes.active
        if (aNd)and(aNd.type in set_gncNdPollTypeTarget):
            if aNd.type=='GROUP':
                if aNd.node_tree:
                    return aNd.node_tree
            else:
                return tree
    return None

class OpGreatGroupConverter(bpy.types.Operator):
    bl_idname = 'node.gnc_op_greatnodeconverter'
    bl_label = "Great Group Converter"
    bl_options = {'UNDO'}
    opt: bpy.props.StringProperty()
    who: bpy.props.StringProperty()
    def execute(self, context):
        global lastConvert
        match self.opt:
            case 'Conv':
                lastConvertTree = RecrDoConvertNodeTree(GetTargetConvert(context.space_data.edit_tree), self.who)
                if not(lastConvertTree in list_lastConverts):
                    list_lastConverts.append(lastConvertTree)
            case 'Add':
                bpy.ops.node.add_node('INVOKE_DEFAULT', type=context.space_data.tree_type.replace("Tree", "Group"), use_transform=True)
                context.space_data.edit_tree.nodes.active.node_tree = bpy.data.node_groups.get(self.who)
        return {'FINISHED'}

dict_mapTreeIco = {'ShaderNodeTree':'NODE_MATERIAL', 'GeometryNodeTree':'GEOMETRY_NODES', 'CompositorNodeTree':'NODE_COMPOSITING', 'TextureNodeTree':'NODE_TEXTURE'}

class PanelGreatGroupConverter(bpy.types.Panel):
    bl_idname = 'GNC_PT_GreatGroupConverter'
    bl_label = "Great Group Converter"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    #bl_category = 'Tool'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 131071
    @classmethod
    def poll(cls, context):
        if list_lastConverts:
            return True
        return GetTargetConvert(context.space_data.edit_tree)
    def draw(self, context):
        colLy = self.layout.column()
        treeTarget = GetTargetConvert(context.space_data.edit_tree)
        colMain = colLy.column(align=True)
        bow = colMain.box()
        bow.scale_y = 0.5
        if treeTarget:
            AddHighlightingText(bow.row(), "Convert", treeTarget.name, "to:")
        else:
            AddHighlightingText(bow.row(), ' ')
        rowConv = colMain.row(align=True)
        rowConv.enabled = not not treeTarget
        for di in dict_mapTreeIco:
            row = rowConv.row(align=True)
            row.scale_x = 2.05
            op = row.operator(OpGreatGroupConverter.bl_idname, text="", icon=dict_mapTreeIco[di])
            op.opt = 'Conv'
            op.who = di
            row.enabled = context.space_data.tree_type!=di
        if list_lastConverts:
            colLasts = colLy.column(align=True)
            bow = colLasts.box()
            bow.scale_y = 0.5
            AddHighlightingText(bow.row(), "", "Last converts:")
            colList = colLasts.box().column(align=True)
            for li in list_lastConverts:
                if str(li).find("invalid")!=-1:
                    list_lastConverts.remove(li)
                    continue
                rowItem = colList.row(align=True)
                rowAdd = rowItem.row(align=True)
                rowAdd.scale_x = 1.45
                op = rowAdd.operator(OpGreatGroupConverter.bl_idname, text="", icon='TRIA_LEFT')
                op.opt = 'Add'
                op.who = li.name
                rowAdd.enabled = li.bl_idname.replace("Group","Tree")==context.space_data.tree_type
                rowName = rowItem.row(align=True)
                rowName.prop(bpy.data.node_groups.get(li.name),'name', text="", icon=dict_mapTreeIco[li.bl_idname])
                rowName.active = rowAdd.enabled

list_classes += [OpGreatGroupConverter, PanelGreatGroupConverter]

def AddLabel(where, txt, tgl=True):
    box = where.box()
    row = box.row(align=True)
    row.alignment = 'CENTER'
    row.label(text=txt)
    row.active = tgl
    box.scale_y = 0.5
def GetBoxLabel(where, txt="", tgl=True):
    col = where.column(align=True)
    if txt:
        AddLabel(col, txt, tgl)
    return col.box()

def Prefs():
    return bpy.context.preferences.addons[addonName].preferences

class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = addonName if __name__=="__main__" else __name__
    suffixMain: bpy.props.StringProperty(name="Main",       default="_GGC"  )
    suffixSh:   bpy.props.StringProperty(name="Shader",     default="_toShd")
    suffixGm:   bpy.props.StringProperty(name="Geometry",   default="_toGeo")
    suffixCp:   bpy.props.StringProperty(name="Compositor", default="_toCmp")
    suffixTx:   bpy.props.StringProperty(name="Texture",    default="_toTex")
    def draw(self, context):
        colLy = self.layout.column()
        box = GetBoxLabel(colLy, "preferences", False)
        colProps = box.column(align=True)
        for k in self.__annotations__.keys():
            colProps.row().prop(self, k)

list_classes += [AddonPrefs]

def register():
    for li in list_classes:
        bpy.utils.register_class(li)
def unregister():
    for li in reversed(list_classes):
        bpy.utils.unregister_class(li)

if __name__=="__main__":
    register()

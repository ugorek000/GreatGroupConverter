bl_info = {'name':"GreatGroupConverter", 'author':"ugorek",
           'version':(2,2,2), 'blender':(4,0,2), 'created':"2024.02.29",
           'description':"Transferring identical nodes between editors.", 'location':"N Panel > Tool",
           'warning':"Non-zero chance of crash in unexplored exceptions", 'category':"Node",
           'wiki_url':"https://github.com/ugorek000/GreatGroupConverter/wiki", 'tracker_url':"https://github.com/ugorek000/GreatGroupConverter/issues"}
addonName = bl_info['name']

from builtins import len as length
import bpy, re
import mathutils

dict_mapTreeIco = {'ShaderNodeTree':'NODE_MATERIAL', 'GeometryNodeTree':'GEOMETRY_NODES', 'CompositorNodeTree':'NODE_COMPOSITING', 'TextureNodeTree':'NODE_TEXTURE'}

def FullCopyFromNode(fromNd, toNd):
    for pr in fromNd.bl_rna.properties:
        #if pr.identifier=='location':
        #    bNd = BNode.GetFields(toNd)
        #    bNd.locx = fromNd.location.x
        #    bNd.locy = fromNd.location.y
        #else
        if (not pr.is_readonly)and(pr.identifier not in {'node_tree', 'bl_idname'}): #На счёт второго не знаю.
            if pr.identifier in toNd.bl_rna.properties: #Для разных нод между Shader и Texture с одинаковым названием; например ShaderNodeTexNoise.
                setattr(toNd, pr.identifier, getattr(fromNd, pr.identifier))
            #Заметка: теперь где-то естественным образом обрабатывается NoiseTexture между ShaderNodeEditor и TextureNodeEditor.
    if hasattr(fromNd,'color_ramp'):
        for pr in fromNd.color_ramp.bl_rna.properties:
            if not pr.is_readonly:
                setattr(toNd.color_ramp, pr.identifier, getattr(fromNd.color_ramp, pr.identifier))
        for cyc in range(length(fromNd.color_ramp.elements)-2):
            toNd.color_ramp.elements.new(0.0)
        for cyc in range(length(fromNd.color_ramp.elements)):
            toNd.color_ramp.elements[cyc].position = fromNd.color_ramp.elements[cyc].position
            toNd.color_ramp.elements[cyc].color    = fromNd.color_ramp.elements[cyc].color
    if hasattr(fromNd,'mapping'):
        for pr in fromNd.mapping.bl_rna.properties:
            if not pr.is_readonly:
                setattr(toNd.mapping, pr.identifier, getattr(fromNd.mapping, pr.identifier))
        for cyc1 in range(length(fromNd.mapping.curves)):
            for cyc2 in range(length(fromNd.mapping.curves[cyc1].points)-2):
                toNd.mapping.curves[cyc1].points.new(0.0, 1.0)
            for cyc2 in range(length(fromNd.mapping.curves[cyc1].points)):
                toNd.mapping.curves[cyc1].points[cyc2].location    = fromNd.mapping.curves[cyc1].points[cyc2].location
                toNd.mapping.curves[cyc1].points[cyc2].handle_type = fromNd.mapping.curves[cyc1].points[cyc2].handle_type

class NodeFiller(bpy.types.Node):
    bl_idname = 'GgcNodeFiller'
    bl_label = "Node Filler"
    bl_width_max = 1024
    bl_width_min = 64
    blid: bpy.props.StringProperty(default="Ggc Node Filler")
    def draw_label(self):
        return self.blid

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
    @classmethod
    def GetFields(cls, tar):
        return cls.from_address(tar.as_pointer())

class BNodeSocketRuntimeHandle(StructBase): #\source\blender\makesdna\DNA_node_types.h
    _pad0:        ctypes.c_char*8
    declaration:  ctypes.c_void_p
    changed_flag: ctypes.c_uint32
    total_inputs: ctypes.c_short
    _pad1:        ctypes.c_char*2
    location:     ctypes.c_float*2
class BNodeStack(StructBase):
    vec:        ctypes.c_float*4
    min:        ctypes.c_float
    max:        ctypes.c_float
    data:       ctypes.c_void_p
    hasinput:   ctypes.c_short
    hasoutput:  ctypes.c_short
    datatype:   ctypes.c_short
    sockettype: ctypes.c_short
    is_copy:    ctypes.c_short
    external:   ctypes.c_short
    _pad:       ctypes.c_char*4
class BNodeSocket(StructBase):
    next:                   ctypes.c_void_p
    prev:                   ctypes.c_void_p
    prop:                   ctypes.c_void_p
    identifier:             ctypes.c_char*64
    name:                   ctypes.c_char*64
    storage:                ctypes.c_void_p
    type:                   ctypes.c_short
    flag:                   ctypes.c_short
    limit:                  ctypes.c_short
    typeinfo:               ctypes.c_void_p
    idname:                 ctypes.c_char*64
    default_value:          ctypes.c_void_p
    _pad:                   ctypes.c_char*4
    label:                  ctypes.c_char*64
    description:            ctypes.c_char*64
    short_label:            ctypes.c_char*64
    default_attribute_name: ctypes.POINTER(ctypes.c_char)
    to_index:               ctypes.c_int
    link:                   ctypes.c_void_p
    ns:                     BNodeStack
    runtime:                ctypes.POINTER(BNodeSocketRuntimeHandle)

class BNode(StructBase): #\source\blender\makesdna\DNA_node_types.h:
    next:       ctypes.c_void_p
    prev:       ctypes.c_void_p
    inputs:     ctypes.c_void_p*2
    outputs:    ctypes.c_void_p*2
    name:       ctypes.c_char*64
    identifier: ctypes.c_int
    flag:       ctypes.c_int
    idname:     ctypes.c_char*64
    typeinfo:   ctypes.c_void_p
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

StructBase.InitStructs()

def GetSocketIndex(sk):
    return int(sk.path_from_id().split(".")[-1].split("[")[-1][:-1])

class RemLink():
    def __init__(self, lk, isSide):
        self.tree = lk.id_data
        self.from_socket = lk.from_socket
        self.from_ndName = lk.from_node.name
        self.from_skName = lk.from_socket.name
        self.from_inx = GetSocketIndex(lk.from_socket)
        self.to_socket = lk.to_socket
        self.to_ndName = lk.to_node.name
        self.to_skName = lk.to_socket.name
        self.to_inx = GetSocketIndex(lk.from_socket)
        self.isSide = isSide
    @property
    def left_socket(self):
        if self.isSide:
            nd = self.tree.nodes[self.from_ndName]
            len = length(nd.outputs)
            return nd.outputs.get(self.from_skName, nd.outputs[self.from_inx] if self.from_inx<len else None) #По именам приоритетнее, потому что.
        else:
            return self.from_socket
    @property
    def right_socket(self):
        if self.isSide:
            return self.to_socket
        else:
            nd = self.tree.nodes[self.to_ndName]
            len = length(nd.inputs)
            return nd.inputs.get(self.to_skName, nd.inputs[self.to_inx] if self.to_inx<len else None)
class RemNode():
    def __init__(self, nd):
        self.nd = nd
        self.tree = nd.id_data
        self.list_remLink = []
        self.list_socketVal = []
def RememberAllLinks(nameTar):
    list_remNode = []
    def RememberLinks(tree):
        for nd in tree.nodes:
            if (nd.type=='GROUP')and(nd.node_tree)and(nd.node_tree.name==nameTar):
                remNode = RemNode(nd)
                for lk in tree.links:
                    if lk.to_node==nd:
                        remNode.list_remLink.append(RemLink(lk, False))
                    elif lk.from_node==nd: #Заметка: elif.
                        remNode.list_remLink.append(RemLink(lk, True))
                for sk in nd.inputs:
                    if 'default_value' in sk.bl_rna.properties:
                        remNode.list_socketVal.append( (sk.name, sk.default_value[:] if getattr(sk.bl_rna.properties['default_value'],'is_array', None) else sk.default_value) )
                list_remNode.append(remNode)
    for ng in bpy.data.node_groups:
        if ng.bl_idname in {'ShaderNodeTree','GeometryNodeTree','CompositorNodeTree','TextureNodeTree'}:
            RememberLinks(ng)
    for att in {'materials', 'worlds', 'lights', 'linestyles', 'scenes', 'textures'}:
        for dt in getattr(bpy.data, att):
            if dt.node_tree:
                RememberLinks(dt.node_tree)
    return list_remNode
def RestoreAllLinks(list_remNode):
    for remNode in list_remNode:
        for remLink in remNode.list_remLink:
            remNode.tree.links.new(remLink.left_socket, remLink.right_socket)
        for li in remNode.list_socketVal: #Восстановить содержимое неподсоединённых сокетов.
            if sk:=remNode.nd.inputs.get(li[0]):
                sk.default_value = li[1]

def TranslateSkfs(treeFrom, treeTo):
    treeTo.interface.clear()
    for skfFrom in treeFrom.interface.items_tree:
        skfTo = treeTo.interface.new_socket(skfFrom.bl_socket_idname, in_out=skfFrom.in_out)
        isSucessType = True
        try:
            skfTo.socket_type = skfFrom.socket_type
        except:
            isSucessType = False
        for pr in skfFrom.bl_rna.properties:
            if (not pr.is_readonly)and(pr.identifier not in {'socket_type','bl_socket_idname'}): #Про 'bl_socket_idname' см.: projects.blender.org/blender/blender/issues/116082 projects.blender.org/blender/blender/issues/116116
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
        if not isSucessType:
            match treeTo.bl_idname:
                case 'ShaderNodeTree':
                    skfTo.socket_type = 'NodeSocketShader'
                case 'GeometryNodeTree':
                    skfTo.socket_type = 'NodeSocketGeometry'
                case 'CompositorNodeTree':
                    skfTo.socket_type = 'NodeSocketColor'
                case 'TextureNodeTree':
                    skfTo.socket_type = 'NodeSocketVector'
            skfTo.name = f"⚠️ {skfTo.name} ‒ '{skfFrom.socket_type}' not found"
            skfTo.hide_value = True

set_omgApiNodesName = {'ShaderNodeOutputAOV'}

def TranslateNodes(treeFrom, treeTo, suffix):
    def OmgSetNodeColor(nd, col): #https://github.com/ugorek000/VoronoiLinker
        if nd.bl_idname=='FunctionNodeInputColor': #https://projects.blender.org/blender/blender/issues/104909
            bn = BNode.GetFields(nd)
            if col:
                bn.color[0] = col[0]
                bn.color[1] = col[1]
                bn.color[2] = col[2]
        else:
            nd.color = col
    treeTo.nodes.clear()
    neTheme = bpy.context.preferences.themes[0].node_editor
    colBg = mathutils.Color(neTheme.node_backdrop[:3])
    #Пайки:
    blidGroupFrom = treeFrom.bl_idname.replace("Tree","Group")
    blidGroupTo = treeTo.bl_idname.replace("Tree","Group")
    blidTo = treeTo.bl_idname
    blidRawTo = blidTo.replace("NodeTree","")
    set_geoExceptions = {'NodeValToRGB','NodeMixRGB','NodeRGBCurve','NodeTexBrick','NodeTexChecker','NodeTexGradient','NodeTexMagic','NodeTexMusgrave',
            'NodeTexNoise','NodeTexVoronoi','NodeTexWave','NodeTexWhiteNoise','NodeClamp','NodeFloatCurve','NodeMapRange','NodeMath','NodeCombineXYZ',
            'NodeSeparateXYZ','NodeVectorCurve','NodeVectorMath','NodeVectorRotate','NodeValue'}
    reQuartetPatt = "^("+"|".join({"Shader", "Geometry", "Compositor", "Texture"})+")"
    def TranslateSkRna(skFrom, skTo):
        for pr in reversed(skFrom.bl_rna.properties):
            if (not pr.is_readonly)and(pr.identifier not in {'type', 'bl_idname'}):
                setattr(skTo, pr.identifier, getattr(skFrom, pr.identifier))
    def TranslateSockets(putsFrom, putsTo):
        for skFrom in putsFrom:
            for skTo in putsTo: #Заметка: Одинаковые имена сокетов у math и vector нода.
                if skTo.identifier==skFrom.identifier: #Заметка: RGBCurve между Shader и Compositor.
                    TranslateSkRna(skFrom, skTo)
                    break
    for ndFrom in treeFrom.nodes:
        try:
            ndTo = None
            blid = ndFrom.bl_idname
            if blid==blidGroupFrom:
                blid = blidGroupTo
            blidTrySame = re.sub(reQuartetPatt, blidRawTo, blid)
            if hasattr(bpy.types, blidTrySame):
                blid = blidTrySame
            blidRaw = re.sub(reQuartetPatt, "", blid)
            if (blidTo=='GeometryNodeTree')and(blidRaw in set_geoExceptions):
                blid = "Shader"+blidRaw
            if blidTo=='CompositorNodeTree':
                blid = {'ShaderNodeRGBCurve':'CompositorNodeCurveRGB', 'ShaderNodeVectorCurve':'CompositorNodeCurveVec'}.get(blid, blid)
            if blidTo in {'ShaderNodeTree', 'GeometryNodeTree'}:
                blid = {'CompositorNodeCurveRGB':'ShaderNodeRGBCurve', 'CompositorNodeCurveVec':'ShaderNodeVectorCurve'}.get(blid, blid)
            ndTo = treeTo.nodes.new(blid)
            FullCopyFromNode(ndFrom, ndTo)
            if ('node_tree' in ndTo.bl_rna.properties)and(ndFrom.node_tree):
                ndTo.node_tree = DoConvertNodeTreeRecr(ndFrom.node_tree, blidTo, suffix)
            assert ndTo.bl_idname!=NodeFiller.bl_idname #В TranslateSockets() теперь по имени, а не по индексу, так что всё ещё "не обломались".
            if ndTo.type=='REROUTE':
                ndTo.inputs[0].type = ndFrom.inputs[0].type
                ndTo.outputs[0].type = ndFrom.outputs[0].type
            TranslateSockets(ndFrom.inputs, ndTo.inputs)
            TranslateSockets(ndFrom.outputs, ndTo.outputs)
        except: #import traceback; pri nt(traceback.format_exc())
            if ndTo: #Для своих NodeFiller, и в целом общее.
                treeTo.nodes.remove(ndTo)
            ndFi = treeTo.nodes.new(NodeFiller.bl_idname)
            ndFi.blid = ndFrom.bl_idname
            for att in 'inputs', 'outputs':
                putsTo = getattr(ndFi, att)
                for skFrom in getattr(ndFrom, att):
                    blid = skFrom.bl_idname
                    #blid = {'NodeSocketGeometry':'NodeSocketMaterial'}.get(blid, blid)
                    skTo = putsTo.new(blid, skFrom.name)
                    TranslateSkRna(skFrom, skTo)
                    if skFrom.is_multi_input:
                        BNodeSocket.GetFields(skTo).flag = 2048
            ndFi.location = ndFrom.location
            #todo0 топологический бардак с этим omg api нодами, а ещё FullCopyFromNode; навести бы порядок.
            if ndFrom.bl_idname in {'CompositorNodeBoxMask', 'CompositorNodeEllipseMask'}: #set_omgApiNodesWidth
                ndFi.width = BNode.GetFields(ndFrom).width
            else:
                ndFi.width = ndFrom.width
            if ndFrom.bl_idname in set_omgApiNodesName:
                BNode.GetFields(ndFi).name = BNode.GetFields(ndFrom).name
            else:
                ndFi.name = ndFrom.name
            ndFi.label = ndFrom.label if ndFrom.label else ndFrom.bl_label
            ndFi.use_custom_color = True
            if ndFrom.bl_idname=='NodeUndefined':
                OmgSetNodeColor(ndFi, (0.633459, 0.226727, 0.226727))
                ndFi.hide = True
            else:
                def MixThCol(col1, col2, fac=0.4): #\source\blender\editors\space_node\node_draw.cc : node_draw_basis() : "Header"
                    return col1*(1-fac)+col2*fac
                OmgSetNodeColor(ndFi, MixThCol(colBg, neTheme.input_node))

def PlaceRerouteFromSocket(skTar, tree=None):
    tree = tree if tree else skTar.id_data
    rr = tree.nodes.new('NodeReroute')
    rr.inputs[0].type = skTar.type
    rr.outputs[0].type = skTar.type
    rr.label = skTar.label if skTar.label else skTar.name
    bNd = BNode.GetFields(rr)
    loc = BNodeSocket.GetFields(skTar).runtime.contents.location
    bNd.locx = loc[0]
    bNd.locy = loc[1]
    return rr
def DoConvertNodeTreeRecr(treeFrom, blidTo, suffix):
    def TranslateLinks(treeFrom, treeTo): #Благодаря гениальной идеи кастомного нода, перенос линков сколлапсировался до 3-х строчек. Огонь!
        def GetSkFromSkHh(nd, skTar):
            for sk in nd.outputs if skTar.is_output else nd.inputs:
                if sk.identifier==skTar.identifier:
                    return sk
            #Заметка: "Factor" у TextureNodeMixRGB и "Fac" у ShaderNodeMixRGB, обрабатывается как есть.
            for sk in nd.outputs if skTar.is_output else nd.inputs: #Эта ветка особо без нужды.
                if (sk.label if sk.label else sk.name)==(skTar.label if skTar.label else skTar.name):
                    return sk
        for lkFrom in treeFrom.links:
            nd = lkFrom.from_node
            nameFrom = BNode.GetFields(nd).name.decode('utf-8') if nd.bl_idname in set_omgApiNodesName else nd.name
            nd = lkFrom.to_node
            nameTo = BNode.GetFields(nd).name.decode('utf-8') if nd.bl_idname in set_omgApiNodesName else nd.name
            ##
            skOut = GetSkFromSkHh(treeTo.nodes[nameFrom], lkFrom.from_socket) #skOut = treeTo.nodes[nameFrom].outputs[GetSocketIndex(lkFrom.from_socket)
            skIn = GetSkFromSkHh(treeTo.nodes[nameTo], lkFrom.to_socket) #skIn = treeTo.nodes[nameTo].inputs[GetSocketIndex(lkFrom.to_socket)]]
            if not skOut:
                skOut = PlaceRerouteFromSocket(lkFrom.from_socket, treeTo).outputs[0]
            if not skIn:
                skIn = PlaceRerouteFromSocket(lkFrom.to_socket, treeTo).inputs[0]
            lkNew = treeTo.links.new(skOut, skIn)
            lkNew.is_valid = lkFrom.is_valid
            lkNew.is_muted = lkFrom.is_muted
            for sk in skIn, skOut: #'GeometryNodeStoreNamedAttribute' в шейдер, см. идентификаторы и ветку по именам в GetSkFromSkHh().
                skIn.enabled = True
                skIn.hide = False
    nameTo = treeFrom.name
    if not nameTo.endswith(suffix):
        nameTo += suffix
    treeTo = bpy.data.node_groups.get(nameTo) or bpy.data.node_groups.new(nameTo, blidTo)
    ##
    list_remNode = RememberAllLinks(nameTo)
    TranslateSkfs(treeFrom, treeTo)
    RestoreAllLinks(list_remNode)
    ##
    TranslateNodes(treeFrom, treeTo, suffix) #Передача suffix для следующей рекурсии. Неплохо было бы бы это как-то подадекватить.
    TranslateLinks(treeFrom, treeTo)
    ##
    for nd in treeTo.nodes:
        nd.select = False
    treeTo.nodes.active = None #Пользовательские "елозенья" от последующих конвертаций.
    return treeTo

#todo0 можно ещё мб переносить ноды с подходящим poll'ом для обоих деревьев полной копией, чтобы вручную свойства не переносить; но это не точно.

def LyAddHighlightingText(where, *args_txt):
    rowRoot = where.row(align=True)
    for cyc, txt in enumerate(args_txt):
        if txt:
            row = rowRoot.row(align=True)
            row.alignment = 'LEFT'
            row.label(text=txt)
            row.active = cyc%2

dict_lastConverts = {}

def GetTargetsToConvert(tree):
    list_result = []
    for nd in tree.nodes:
        if nd.select:
            match nd.type:
                case 'GROUP':
                    if nd.node_tree:
                        list_result.append(nd.node_tree)
                case 'GROUP_INPUT'|'GROUP_OUTPUT':
                    list_result.append(tree)
    return list_result

class OpGreatGroupConverter(bpy.types.Operator):
    bl_idname = 'node.greatgroupconverter'
    bl_label = "Great Group Converter"
    bl_options = {'UNDO'}
    opt: bpy.props.StringProperty()
    who: bpy.props.StringProperty()
    def execute(self, context):
        match self.opt:
            case 'Conv':
                suffix = Prefs().txtSuffixMain+getattr(Prefs(), *[att for att in {'txtSuffixSh', 'txtSuffixGm', 'txtSuffixCp', 'txtSuffixTx'} if att[9]==self.who[0]])
                for li in GetTargetsToConvert(context.space_data.edit_tree):
                    tree = DoConvertNodeTreeRecr(li, self.who, suffix)
                    dict_lastConverts[tree] = tree.name
            case 'Add':
                bpy.ops.node.add_node('INVOKE_DEFAULT', type=context.space_data.tree_type.replace("Tree", "Group"), use_transform=True)
                context.space_data.edit_tree.nodes.active.node_tree = bpy.data.node_groups.get(self.who)
        return {'FINISHED'}

class PanelGreatGroupConverter(bpy.types.Panel):
    bl_idname = 'GGC_PT_GreatGroupConverter'
    bl_label = "Great Group Converter"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 131071
    @classmethod
    def poll(cls, context):
        return not not context.space_data.edit_tree
    def draw(self, context):
        colLy = self.layout.column()
        tree = context.space_data.edit_tree
        blidTree = tree.bl_idname
        colMain = colLy.column(align=True)
        boxTar = colMain.box()
        boxTar.scale_y = 0.5
        list_targets = GetTargetsToConvert(tree)
        if list_targets:
            for li in list_targets:
                LyAddHighlightingText(boxTar.row(), "Convert", li.name, "to"+":"*(li==tree)) #todo0 ctypes масштаб региона, и если текст не вмещается, показывать только имена.
        else:
            LyAddHighlightingText(boxTar.row(), 'none to selected')
        ##
        rowConv = colMain.row(align=True)
        rowConv.enabled = not not list_targets
        for dk, dv in dict_mapTreeIco.items():
            row = rowConv.row(align=True)
            row.scale_x = 2.08 #Начиная с `2.05` оно будет в заполняющем виде; 2.08 -- для 'view.ui_scale'.
            row.enabled = blidTree!=dk
            op = row.operator(OpGreatGroupConverter.bl_idname, text="", icon=dv)
            op.opt = 'Conv'
            op.who = dk
        ##
        if dict_lastConverts:
            colLasts = colLy.column(align=True)
            boxLabel = colLasts.box()
            boxLabel.scale_y = 0.6
            LyAddHighlightingText(boxLabel.row(), "", "Last converts:")
            colList = colLasts.box().column(align=True)
            aNd = tree.nodes.active
            soldTreeNg = aNd.node_tree if (aNd)and(aNd.select)and(aNd.type=='GROUP') else None
            isSucessTgl = True
            while isSucessTgl:
                isSucessTgl = False
                for dk, dv in dict_lastConverts.items():
                    if str(dk).find("invalid")!=-1: #bpy.data.node_groups.get(dv, None) is None:
                        del dict_lastConverts[dk]
                        isSucessTgl = True
                        break
            for ng in reversed(dict_lastConverts):
                rowItem = colList.row().row(align=True)
                rowItem.active = ng.bl_idname==blidTree
                rowAdd = rowItem.row(align=True)
                rowAdd.scale_x = 1.45
                rowAdd.enabled = rowItem.active
                op = rowAdd.operator(OpGreatGroupConverter.bl_idname, text="", icon='TRIA_LEFT', depress=(ng==soldTreeNg) if soldTreeNg else False)
                op.opt = 'Add'
                op.who = ng.name
                rowName = rowItem.row(align=True)
                rowName.prop(ng,'name', text="", icon=ng.bl_icon)

def Prefs():
    return bpy.context.preferences.addons[addonName].preferences

class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = addonName
    txtSuffixMain: bpy.props.StringProperty(name="Main",       default="_GGC"  )
    #Нужно сохранять порядок с dict_mapTreeIco:
    txtSuffixSh:   bpy.props.StringProperty(name="Shader",     default="_toShad")
    txtSuffixGm:   bpy.props.StringProperty(name="Geometry",   default="_toGeo")
    txtSuffixCp:   bpy.props.StringProperty(name="Compositor", default="_toComp")
    txtSuffixTx:   bpy.props.StringProperty(name="Texture",    default="_toTex")
    def draw(self, context):
        col = self.layout.column(align=True)
        box = col.box()
        box.scale_y = 0.5
        row = box.row(align=True)
        row.alignment = 'CENTER'
        row.label(text="Suffixes")
        row.active = False
        row = col.box().row(align=True)
        for att, ico in zip(self.__annotations__.keys(), ['NODETREE']+list(dict_mapTreeIco.values())):
            row.row().prop(self, att, text="", icon=ico)

list_clsToReg = []
def register():
    from gc import collect
    collect(); del collect
    tup_typesToReg = (getattr(bpy.types, att) for att in "Node Operator Panel AddonPreferences".split(" "))
    set_globals = set((dv for dk, dv in dict(globals()).items() if not( (dv.__class__ in {dict, set, list})or(dk=='__spec__') )))
    list_clsToReg.clear() #Заметка: нужно для перерегистраций.
    def RecrToReg(list_subs):
        for li in list_subs:
            list_clsToReg.append(li)
            RecrToReg(li.__subclasses__())
    RecrToReg([si for tp in tup_typesToReg for si in set_globals.intersection(set((li for li in tp.__subclasses__() if li.__module__==__name__)))])
    for li in list_clsToReg:
        bpy.utils.register_class(li)
def unregister():
    for li in reversed(list_clsToReg):
        bpy.utils.unregister_class(li)

if __name__=="__main__":
    register()

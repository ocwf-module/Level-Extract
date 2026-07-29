import xml.etree.ElementTree as ET
import os
import zipfile
from pathlib import Path
import shutil
from shutil import move
import struct
import uuid
import re

def Generate_GUID(): # Код для генерации особого вида UUID (GUID)
    # Версия на C++: https://gist.github.com/fernandomv3/46a6d7656f50ee8d39dc
    return "{" + str(uuid.uuid4()).upper() + "}" # В качестве альтернативы можно использовать встроенный модуль "uuid" Python

def Generate_GUID_from_GUID64(GUID64): # Конвертируем GUID64 в особый UUID (GUID) для CryEngine
    return "{" + f"{GUID64[8:]}-{GUID64[4:8]}-{GUID64[0:4]}-{GUID64[0:4]}-{GUID64[8:]}{GUID64[0:4]}" + "}"

def Cache_the_GUID(Mission_Mission0): # Кэшируем значения: EntityId, GUID64 и GUID для быстрого поиска и использования в сопоставлении Entity в дальнейшем
    print('- The process of caching GUID values has begun. The duration of the process depends on the size of the level...')
    with open('GUID_Cache.xml', 'w', encoding='utf-8') as f:
        f.write('<DataBase Description="Caching of [EntityId], [GUID64], and [GUID] values for matching entities.">\n\t<Values>\n\t</Values>\n</DataBase>')
    GUID_Cache = ET.parse('GUID_Cache.xml')
    GUID_Cache_root = GUID_Cache.getroot()
    Values = GUID_Cache_root.find('Values')
    New_Elements = []
    for Entity in Mission_Mission0.findall('Objects/Entity'):
        if Entity.get('EntityGuid'):
            EntityId = Entity.get('EntityId')
            GUID64 = Entity.get('EntityGuid')
            for FlowGraph in Mission_Mission0.findall('Objects/Entity/FlowGraph/Nodes/Node'):
                if FlowGraph.get('EntityGUID_64') == GUID64:
                    New_Element = ET.Element('Value')
                    New_Element.set('EntityId', EntityId)
                    New_Element.set('GUID64', GUID64)
                    New_Element.set('GUID', FlowGraph.get('EntityGUID'))
                    New_Element.set('Random', 'False')
                    New_Elements.append(New_Element)
                    break
            else:
                New_Element = ET.Element('Value')
                New_Element.set('EntityId', EntityId)
                New_Element.set('GUID64', GUID64)
                New_Element.set('GUID', Generate_GUID_from_GUID64(GUID64))
                New_Element.set('Random', 'True')
                New_Elements.append(New_Element)
    Values.extend(New_Elements)
    ET.indent(GUID_Cache, space='\t', level=0)
    GUID_Cache.write('GUID_Cache.xml', encoding='utf-8', xml_declaration=True)
    GUID_Cache = ET.parse('GUID_Cache.xml').getroot()
    print('- The process of caching GUID values is completed.')
    return GUID_Cache.findall('Values/Value')

def Search_GUID(GUID_Cache, EntityId):
    for Value in GUID_Cache:
        if Value.attrib['EntityId'] == EntityId:
            return Value.attrib['GUID']
    else:
        print(f"⚠️ [{EntityId}] not found in [GUID_Cache.xml]!")

def Search_Archetype_GUID(Library, Archetype):
    for file in os.listdir('EntityArchetypes'):
        if file.endswith('.xml'):
            EntityPrototypeLibrary = ET.parse(f"EntityArchetypes\\{file}").getroot()
            if EntityPrototypeLibrary.get('Name') == Library:
                for EntityPrototype in EntityPrototypeLibrary.findall('EntityPrototype'):
                    if EntityPrototype.attrib['Name'] == Archetype:
                        return EntityPrototype.attrib['Id']
                else:
                    print(f"⚠️ [{Archetype}] was not found in the database [{EntityPrototypeLibrary}]!")
                    return "{00000000-0000-0000-0000-000000000000}"
    else:
        print(f"⚠️ [{Archetype}] was not found in the database [Libs\\EntityArchetypes\\]!")
        return "{00000000-0000-0000-0000-000000000000}"

def Coordinate_Subtraction(pos, point):
    coords1 = list(map(float, pos.split(',')))
    coords2 = list(map(float, point.split(',')))
    result = [coord2 - coord1 for coord1, coord2 in zip(coords1, coords2)]
    return ','.join(str(x) for x in result)

def Create_LYR(Name_LYR, NameLevel):
    Path_FileName_LYR = f"{NameLevel}\\Setting\\Layers\\{Name_LYR}.lyr"
    Object_Layer = ET.Element('ObjectLayer')
    Layer_Element = ET.SubElement(Object_Layer, 'Layer')
    Layer_Element.set('Name', Name_LYR)
    Layer_Element.set('GUID', Generate_GUID())
    Layer_Element.set('Hidden', '0')
    Layer_Element.set('Frozen', '0')
    Layer_Element.set('External', '0')
    Layer_Element.set('Exportable', '1')
    Layer_Element.set('ExportLayerPak', '1')
    Layer_Element.set('DefaultLoaded', '0')
    Layer_Element.set('HavePhysics', '1')
    Layer_Element.set('Expanded', '1')
    Layer_Element.set('IsDefaultColor', '1')
    Layer_Objects = ET.SubElement(Layer_Element, 'LayerObjects')
    lyr_tree = ET.ElementTree(Object_Layer)
    ET.indent(lyr_tree, space='\t', level=0)
    lyr_tree.write(Path_FileName_LYR, encoding='utf-8', xml_declaration=True)
    print(f'- File created: {Path_FileName_LYR}')

def Write_to_LYR(Name_LYR, New_Object, NameLevel):
    tree = ET.parse(f'{NameLevel}\\Setting\\Layers\\{Name_LYR}.lyr')
    root = tree.getroot()
    LayerObjects = root.find('Layer/LayerObjects')
    LayerObjects.append(New_Object)
    ET.indent(tree, space='\t', level=0)
    tree.write(f'{NameLevel}\\Setting\\Layers\\{Name_LYR}.lyr', encoding='utf-8', xml_declaration=True)

def Processing_the_Entities_Array(Entities, AI_Spawners_Presets, NameLevel):
    for Entity in Entities:
        New_Object = ET.Element('Object')
        for attr_name, attr_value in Entity.attrib.items():
            if attr_name not in ['EntityId', 'EntityGuid', 'ParentId', 'Archetype']:
                New_Object.set(attr_name, attr_value)
        for child in Entity:
            New_Object.append(child)
        if Entity.get('EntityClass') == "AreaBox":
            New_Object.set('Type', 'AreaBox')
            if New_Object.find('Area') is not None:
                New_Object.remove(New_Object.find('Area'))
            Area = Entity.find('Area')
            if Area is not None:
                New_Object.set('AreaId', Area.get('Id'))
                New_Object.set('GroupId', Area.get('Group'))
                New_Object.set('Priority', Area.get('Priority'))
                New_Object.set('BoxMin', Area.get('BoxMin'))
                New_Object.set('BoxMax', Area.get('BoxMax'))
            Entities_in_Area = Area.find('Entities')
            if Entities_in_Area is not None:
                New_Object.append(Entities_in_Area)
            if Entity.find('Area/SoundData') is not None:
                SoundData = {}
                for Side_Number in range(1, 7):
                    Side = Entity.find(f'Area/SoundData/Side{Side_Number}')
                    if Side is not None:
                        SoundData[f'Side{Side_Number}'] = Side.get('ObstructSound')
                New_Side = ET.SubElement(New_Object, 'SoundData')
                for attr_name, attr_value in SoundData.items():
                    New_Side.set(attr_name, attr_value)
        elif Entity.get('EntityClass') == "AreaShape":
            New_Object.set('Type', 'Shape')
            if New_Object.find('Area') is not None:
                New_Object.remove(New_Object.find('Area'))
            Area = Entity.find('Area')
            if Area is not None:
                New_Object.set('AreaId', Area.get('Id'))
                New_Object.set('GroupId', Area.get('Group'))
                New_Object.set('Priority', Area.get('Priority'))
                New_Object.set('Height', Area.get('Height'))
            Points_in_Area = Area.find('Points')
            if Points_in_Area is not None:
                New_Object.append(Points_in_Area)
            Entities_in_Area = Area.find('Entities')
            if Entities_in_Area is not None:
                New_Object.append(Entities_in_Area)
        elif Entity.get('EntityClass') == "AreaSphere":
            New_Object.set('Type', 'AreaSphere')
            if New_Object.find('Area') is not None:
                New_Object.remove(New_Object.find('Area'))
            Area = Entity.find('Area')
            if Area is not None:
                New_Object.set('AreaId', Area.get('Id'))
                New_Object.set('GroupId', Area.get('Group'))
                New_Object.set('Priority', Area.get('Priority'))
                New_Object.set('Radius', Area.get('SphereRadius'))
            Entities_in_Area = Area.find('Entities')
            if Entities_in_Area is not None:
                New_Object.append(Entities_in_Area)
        elif Entity.get('EntityClass') == "LightBox":
            New_Object.set('Type', 'LightBox')
            if New_Object.find('Area') is not None:
                New_Object.remove(New_Object.find('Area'))
            Area = Entity.find('Area')
            if Area is not None:
                New_Object.set('AreaId', Area.get('Id'))
                New_Object.set('GroupId', Area.get('Group'))
                New_Object.set('Priority', Area.get('Priority'))
                New_Object.set('BoxMin', Area.get('BoxMin'))
                New_Object.set('BoxMax', Area.get('BoxMax'))
            Entities_in_Area = Area.find('Entities')
            if Entities_in_Area is not None:
                New_Object.append(Entities_in_Area)
        elif Entity.get('EntityClass') == "LightShape":
            New_Object.set('Type', 'LightShape')
            if New_Object.find('Area') is not None:
                New_Object.remove(New_Object.find('Area'))
            Area = Entity.find('Area')
            if Area is not None:
                New_Object.set('AreaId', Area.get('Id'))
                New_Object.set('GroupId', Area.get('Group'))
                New_Object.set('Priority', Area.get('Priority'))
                New_Object.set('Height', Area.get('Height'))
            Points_in_Area = Area.find('Points')
            if Points_in_Area is not None:
                New_Object.append(Points_in_Area)
            Entities_in_Area = Area.find('Entities')
            if Entities_in_Area is not None:
                New_Object.append(Entities_in_Area)
        elif Entity.get('EntityClass') == "CameraSource":
            New_Object.set('Type', 'Camera')
        elif Entity.get('EntityClass') == "CharacterAttachHelper":
            New_Object.set('Type', 'CharAttachHelper')
        elif Entity.get('EntityClass') == "RopeEntity":
            New_Object.set('Type', 'Rope')
        elif Entity.get('EntityClass') == "TestWaypoint":
            New_Object.set('Type', 'TestWaypoint')
            if New_Object.find('CustomProperties') is not None:
                New_Object.remove(New_Object.find('CustomProperties'))
            for Property in Entity.findall('CustomProperties/Property'):
                if Property.attrib['name'] == "action":
                    New_Object.set('ActionType', Property.attrib['value'])
                elif Property.attrib['name'] == "execTimeCmd":
                    New_Object.set('ExecuteTime', Property.attrib['value'])
                elif Property.attrib['name'] == "teleport":
                    New_Object.set('Teleport', Property.attrib['value'])
                elif Property.attrib['name'] == "numberParam":
                    New_Object.set('Number', Property.attrib['value'])
                elif Property.attrib['name'] == "stringParam":
                    New_Object.set('String', Property.attrib['value'])
                New_Object.set('StartWaypoint', '')
        elif Entity.get('EntityClass') == "EnvironmentLight":
            New_Object.set('Type', 'EnvironmentProbe')
        elif Entity.get('Archetype') is not None:
            New_Object.set('Type', 'EntityArchetype')
            Library = Entity.get('Archetype')
            if Library is not None:
                Library = Library.split('.', 1)[0]
                if Library not in Entity_Library:
                    Entity_Library.append(Library)
            Archetype = Entity.get('Archetype')
            if Archetype is not None:
                Archetype = Archetype.split('.', 1)[1]
                New_Object.set('Prototype', Search_Archetype_GUID(Library, Archetype))
        elif Entity.get('EntityClass') == "AISpawner":
            Properties = Entity.find('Properties')
            SpawnerPreset = Properties.get('SpawnerPreset')
            for Preset in AI_Spawners_Presets:
                if Preset.get('name') == SpawnerPreset:
                    Library = Entity.get('Archetype')
                    if Library is not None:
                        Library = Library.split('.', 1)[0]
                        if Library not in Entity_Library:
                            Entity_Library.append(Library)
                            break
            else:
                print(f"⚠️ The library for the preset [{SpawnerPreset}] was not found!")
        elif Entity.get('EntityClass') in ["GeomEntity", "ReverbVolume", "SoundMoodVolume", "SoundSpot", "MusicMoodSelector", "MusicEndTheme", "MusicLogicTrigger", "AmbientVolume", "MusicPlayPattern", "SoundEventSpot", "RandomSoundVolume", "MusicThemeSelector", "MusicStinger", "Dialog", "AIPathPoint", "NavigationSeedPoint", "AIAnchor", "TagPoint", "SmartObject"]:
            New_Object.set('Type', Entity.get('EntityClass'))
        else:
            New_Object.set('Type', 'Entity')
        New_Object.set('Id', Search_GUID(GUID_Cache, Entity.get('EntityId')))
        if Entity.get('ParentId') is not None:
            New_Object.set('Parent', Search_GUID(GUID_Cache, Entity.get('ParentId')))
        if Entity.get('Pos') is None:
            New_Object.set('Pos', '0,0,0')
        if Entity.get('Rotate') is None:
            New_Object.set('Rotate', '1,0,0,0')
        if Entity.get('Scale') is None:
            New_Object.set('Scale', '1,1,1')
        EntityLinks1 = New_Object.findall('EntityLinks/Link')
        if EntityLinks1 is not None:
            for EntityLink in EntityLinks1:
                EntityLink.set('TargetId', Search_GUID(GUID_Cache, EntityLink.get('TargetId')))
        EntityLinks2 = New_Object.findall('Entities/Entity')
        if EntityLinks2 is not None:
            for EntityLink in EntityLinks2:
                EntityLink.set('Id', Search_GUID(GUID_Cache, EntityLink.get('Id')))
        if New_Object.get('Layer') is not None:
            Write_to_LYR(New_Object.get('Layer'), New_Object, NameLevel)
        else:
            New_Object.set('Layer', 'LE_Others')
            Write_to_LYR('LE_Others', New_Object, NameLevel)

def Processing_the_Objects_Array(Objects, NameLevel):
    for Object in Objects:
        New_Object = ET.Element('Object')
        for attr_name, attr_value in Object.attrib.items():
            if attr_name != "ParentId":
                New_Object.set(attr_name, attr_value)
        for child in Object:
            New_Object.append(child)
        if Object.get('Type') == "Decal":
            New_Object.set('Layer', 'LE_Decals')
        if Object.get('Type') == "OccluderArea":
            New_Object.set('EntityClass', 'AreaShape')
            New_Object.set('Rotate', '1,0,0,0')
            New_Object.set('Layer', 'LE_Occluders')
            Points_List = Object.findall('Points/Point')
            if Points_List is not None:
                level = 1
                for Point in Points_List:
                    if level == 1:
                        Point.set('Pos', '0,0,0')
                        level += 1
                    else:
                        Point.set('Pos', Coordinate_Subtraction(Object.get('Pos'), Point.get('Pos')))
        elif Object.get('Type') == "OccluderPlane":
            New_Object.set('EntityClass', 'AreaShape')
            New_Object.set('Rotate', '1,0,0,0')
            New_Object.set('Layer', 'LE_Occluders')
            Points_List = Object.findall('Points/Point')
            if Points_List is not None:
                level = 1
                for Point in Points_List:
                    if level == 1:
                        Point.set('Pos', '0,0,0')
                        level += 1
                    else:
                        Point.set('Pos', Coordinate_Subtraction(Object.get('Pos'), Point.get('Pos')))
        elif Object.get('Type') == "Portal":
            New_Object.set('EntityClass', 'AreaShape')
            New_Object.set('Rotate', '1,0,0,0')
            New_Object.set('Layer', 'LE_Portals')
            Points_List = Object.findall('Points/Point')
            if Points_List is not None:
                level = 1
                for Point in Points_List:
                    if level == 1:
                        Point.set('Pos', '0,0,0')
                        level += 1
                    else:
                        Point.set('Pos', Coordinate_Subtraction(Object.get('Pos'), Point.get('Pos')))
        elif Object.get('Type') == "VisArea":
            New_Object.set('EntityClass', 'AreaShape')
            New_Object.set('Rotate', '1,0,0,0')
            New_Object.set('Layer', 'LE_VisAreas')
            Points_List = Object.findall('Points/Point')
            if Points_List is not None:
                level = 1
                for Point in Points_List:
                    if level == 1:
                        Point.set('Pos', '0,0,0')
                        level += 1
                    else:
                        Point.set('Pos', Coordinate_Subtraction(Object.get('Pos'), Point.get('Pos')))
        elif Object.get('Type') == "SequenceObject":
            for Sequence in MovieData.findall('Mission/SequenceData/Sequence'):
                if Object.get('Name') == Sequence.get('Name'):
                    New_Object.append(Sequence)
            New_Object.set('Layer', 'LE_SequenceObjects')
        else:
            if Object.get('Type') is not None:
                New_Object.set('Type', Object.get('Type'))
            else:
                New_Object.set('Type', 'Objects')
        New_Object.set('Id', Generate_GUID())
        if Object.get('Pos') is None:
            New_Object.set('Pos', '0,0,0')
        if Object.get('Rotate') is None:
            New_Object.set('Rotate', '1,0,0,0')
        if Object.get('Scale') is None:
            New_Object.set('Scale', '1,1,1')
        EntityLinks1 = New_Object.findall('EntityLinks/Link')
        if EntityLinks1 is not None:
            for EntityLink in EntityLinks1:
                EntityLink.set('TargetId', Search_GUID(GUID_Cache, EntityLink.get('TargetId')))
        EntityLinks2 = New_Object.findall('Entities/Entity')
        if EntityLinks2 is not None:
            for EntityLink in EntityLinks2:
                EntityLink.set('Id', Search_GUID(GUID_Cache, EntityLink.get('Id')))
        if New_Object.get('Layer') is not None:
            Write_to_LYR(New_Object.get('Layer'), New_Object, NameLevel)
        else:
            New_Object.set('Layer', 'LE_Others')
            Write_to_LYR('LE_Others', New_Object, NameLevel)

def Create_File_TerrainLayerSettings_lay(LevelData, NameLevel):
    print('- The process of creating the [TerrainTextureLayers.lay] level file has begun...')
    with open(f'{NameLevel}\\Setting\\Terrain\\TerrainTextureLayers.xml', 'w') as f:
        f.write('<LayerSettings>\n\t<SurfaceTypes>\n\t</SurfaceTypes>\n\t<Layers>\n\t</Layers>\n</LayerSettings>')
    tree = ET.parse(f'{NameLevel}\\Setting\\Terrain\\TerrainTextureLayers.xml')
    root = tree.getroot()
    SurfaceTypes = root.find('SurfaceTypes')
    Layers = root.find('Layers')
    Index = 1
    for SurfaceType in LevelData.findall('SurfaceTypes/SurfaceType'):
        SurfaceTypes.append(SurfaceType)
        New_Layer = ET.Element('Layer')
        New_Layer.set('Name', SurfaceType.get('Name').split('/')[-1])
        New_Layer.set('Texture', 'textures/terrain/64gray.dds')
        New_Layer.set('TextureWidth', '64')
        New_Layer.set('TextureHeight', '64')
        New_Layer.set('Material', '')
        New_Layer.set('AltStart', '0')
        New_Layer.set('AltEnd', '4096')
        New_Layer.set('MinSlopeAngle', '0')
        New_Layer.set('MaxSlopeAngle', '90')
        New_Layer.set('InUse', '1')
        New_Layer.set('AutoGenMask', '1')
        New_Layer.set('LayerId', str(Index))
        New_Layer.set('SurfaceType', SurfaceType.get('Name'))
        New_Layer.set('FilterColor', '0,0,0')
        New_Layer.set('LayerBrightness', '0.5')
        New_Layer.set('UseRemeshing', '0')
        New_Layer.set('LayerTiling', '1')
        New_Layer.set('SpecularAmount', '0')
        New_Layer.set('SortOrder', '0')
        Layers.append(New_Layer)
        Index += 1
    ET.indent(tree, space='\t', level=0)
    tree.write(f'{NameLevel}\\Setting\\Terrain\\TerrainTextureLayers.xml', encoding='utf-8', xml_declaration=True)
    with open(f'{NameLevel}\\Setting\\Terrain\\TerrainTextureLayers.lay', 'wb') as f: # При создании файла [.lay] необходимо:
        # 1. Вычислить размер XML-структуры в 16-битном беззнаковом целом числе;
        # 2. Записать число 255 в шестнадцатеричном виде, а после размер XML-структуры в самом начале файла;
        # 3. Записать XML-структуру;
        # 4. Записать 4 бинарных нуля;
        f.write(struct.pack('B', 255)) # holder-байт
        f.write(struct.pack('<H', 0)) # placeholder для xml_size
        start_pos = f.tell()
        with open(f'{NameLevel}\\Setting\\Terrain\\TerrainTextureLayers.xml', 'rb') as fr:
            f.write(fr.read())
        for _ in range(4):
            f.write(struct.pack('B', 0))
        end_pos = f.tell()
        xml_size = end_pos - start_pos - 4 # Минус 4 нулевых байта
        f.seek(1) # Пропускаем holder-байт
        f.write(struct.pack('<H', xml_size))
        f.seek(0, 2)
    os.remove(f'{NameLevel}\\Setting\\Terrain\\TerrainTextureLayers.xml')
    print('- The process of creating the [TerrainTextureLayers.lay] level file is completed.')

def Extract_ToD(Mission_Mission0, NameLevel):
    print('- The process of extracting the [TimeOfDay.tod] level file has begun...')
    TimeOfDay = Mission_Mission0.find('TimeOfDay')
    if TimeOfDay is not None:
        tree = ET.ElementTree(TimeOfDay)
        ET.indent(tree, space='\t', level=0)
        tree.write(f'{NameLevel}\\Setting\\TOD_and_Lighting\\TimeOfDay.tod', encoding='utf-8', xml_declaration=True)
        print('- The process of extracting a file of the [TimeOfDay.tod] completed.')
    else:
        print('- The process of extracting a file of the [TimeOfDay.tod] was interrupted due to lack of necessary data.')

def Extract_LightSettings(Mission_Mission0, NameLevel):
    print('- The process of extracting the [LightSettings.lgt] level file has begun...')
    Lighting = Mission_Mission0.find('Environment/Lighting')
    if Lighting is not None:
        LightSettings = ET.Element('LightSettings')
        LightSettings.append(Lighting)
        tree = ET.ElementTree(LightSettings)
        ET.indent(tree, space='\t', level=0)
        tree.write(f'{NameLevel}\\Setting\\TOD_and_Lighting\\LightSettings.lgt', encoding='utf-8', xml_declaration=True)
        print('- The process of extracting a file of the [LightSettings.lgt] completed.')
    else:
        print('- The process of extracting a file of the [LightSettings.lgt] was interrupted due to lack of necessary data.')

def Extract_Library(Entity_Library, Particles_Library, GameTokens_Library, LevelData, LevelDataAction, NameLevel):
    print('- The file creation process has started [Preload_Library.xml]...')
    for ParticlesLibrary in LevelData.findall('ParticlesLibrary/Library'):
        Particles_Library.append(ParticlesLibrary.get('Name'))
    for GameTokensLibrary in LevelData.findall('GameTokensLibraryReferences/Library'):
        GameTokens_Library.append(GameTokensLibrary.get('Name'))
    MusicLibraries = []
    for MusicLibrary in LevelDataAction.findall('MusicLibrary/Library'):
        MusicLibraries.append(MusicLibrary.get('Name'))
    with open(f'{NameLevel}\\Setting\\Preload_Library.xml', 'w', encoding='utf-8') as f:
        f.write('<DataBase Description="It contains the names of libraries that must be imported before importing layers.">\n\t<EntityLibrary>\n\t</EntityLibrary>\n\t<ParticlesLibrary>\n\t</ParticlesLibrary>\n\t<GameTokensLibrary>\n\t</GameTokensLibrary>\n\t<MusicLibrary>\n\t</MusicLibrary>\n</DataBase>')
    Preload_Library = ET.parse(f'{NameLevel}\\Setting\\Preload_Library.xml')
    Preload_Library_root = Preload_Library.getroot()
    EntityLibrary = Preload_Library_root.find('EntityLibrary')
    for Library in Entity_Library:
        New_Element = ET.Element('Library')
        New_Element.set('Name', Library)
        EntityLibrary.append(New_Element)
    ParticlesLibrary = Preload_Library_root.find('ParticlesLibrary')
    for Library in Particles_Library:
        New_Element = ET.Element('Library')
        New_Element.set('Name', Library)
        ParticlesLibrary.append(New_Element)
    GameTokensLibrary = Preload_Library_root.find('GameTokensLibrary')
    for Library in GameTokens_Library:
        New_Element = ET.Element('Library')
        New_Element.set('Name', Library)
        GameTokensLibrary.append(New_Element)
    MusicLibrary = Preload_Library_root.find('MusicLibrary')
    for Library in MusicLibraries:
        New_Element = ET.Element('Library')
        New_Element.set('Name', Library)
        MusicLibrary.append(New_Element)
    ET.indent(Preload_Library, space='\t', level=0)
    Preload_Library.write(f'{NameLevel}\\Setting\\Preload_Library.xml', encoding='utf-8', xml_declaration=True)
    print('- The file creation process [Preload_Library.xml] completed.')

def Processing_of_NUX_MOD_SDK_Layers(LevelData, NameLevel, Layers):
    print('- The process of processing the files extracted by [NUX_MOD_SDK] has begun. The duration of the process depends on the size of the level...')
    for file in os.listdir('NUX_MOD_SDK'):
        if file.endswith('.lyr'):
            try:
                LYR_File = ET.parse(f'NUX_MOD_SDK\\{file}').getroot()
                Layer = LYR_File.find('Layer')
                for Object in Layer.findall('LayerObjects/Object'):
                    if Object.get('Type') in ['Brush', 'WaterVolume', 'Road']:
                        Name_LYR = Layer.get('Name')
                        if Name_LYR == "CLC_0":
                            Name_LYR = "LE_Unknown_Layer"
                        if Name_LYR not in Layers:
                            Create_LYR(Name_LYR, NameLevel)
                            Layers.append(Name_LYR)
                        Object.set('Layer', Name_LYR)
                        Write_to_LYR(Name_LYR, Object, NameLevel)
            except Exception as e:
                print(f'Error: couldn`t process the file [{file}]. Learn more: {e}')
        if file == "vegetationWF.veg":
            VEG_File = ET.parse(f'NUX_MOD_SDK\\{file}').getroot()
            Vegetation = ET.Element('Vegetation')
            for Object in LevelData.findall('Vegetation/Object'):
                New_Object = ET.Element('VegetationObject')
                for attr_name, attr_value in Object.attrib.items():
                    if attr_name == "Object":
                        New_Object.set('FileName', attr_value)
                    else:
                        New_Object.set(attr_name, attr_value)
                for VegetationObject in VEG_File.findall('VegetationObject'):
                    if New_Object.get('FileName') == VegetationObject.get('FileName') and VegetationObject.find('Instances') is not None:
                        New_Object.append(VegetationObject.find('Instances'))
                Vegetation.append(New_Object)
            tree = ET.ElementTree(Vegetation)
            ET.indent(tree, space='\t', level=0)
            tree.write(f'{NameLevel}\\Setting\\Vegetation\\Vegetation.veg', encoding='utf-8', xml_declaration=True)
        if file == "terrain.trb":
            with open(f'NUX_MOD_SDK\\{file}', 'rb') as f:
                data = f.read()
            match = re.search(rb"<\?xml.*?</Root>", data, re.DOTALL)
            if match is not None:
                with open(f'{NameLevel}\\Setting\\Terrain\\TerrainInfo.xml', 'w') as f:
                    f.write(match.group(0).decode('utf-8'))
                TerrainInfo_File = ET.parse(f'{NameLevel}\\Setting\\Terrain\\TerrainInfo.xml').getroot()
                Terrain = TerrainInfo_File.find('Heightmap')
                Terrain_Width = Terrain.get('Width')
                Terrain_Height = Terrain.get('Height')
                Terrain_Unit = Terrain.get('UnitSize')
                os.rename(f'NUX_MOD_SDK\\{file}', f'{NameLevel}\\Setting\\Terrain\\Terrain_{Terrain_Width}x{Terrain_Height}_UnitSize_{Terrain_Unit}.trb')
                print('- The processing of the files extracted by [NUX_MOD_SDK] has been completed.')
            else:
                os.rename(f'NUX_MOD_SDK\\{file}', f'{NameLevel}\\Setting\\Terrain\\Terrain_XxX_UnitSize_X.trb')
                print('- The process of renaming the [terrain.trb] file was interrupted due to the lack of necessary data. The file was copied to the working directory without details in the name.')

def Processing_of_CryDumper_Layer(NameLevel):
    print('- The process of processing the files extracted by [CryDumper] has begun. The duration of the process depends on the size of the level...')
    LYR_File = ET.parse(f'CryDumper\\ai_points_dump.lyr').getroot()
    for Object in LYR_File.findall('Layer/LayerObjects/Object'):
        if Object.get('Type') == "AIPoint":
            Object.set('Id', Generate_GUID())
            Object.set('Layer', 'LE_AIPoints')
            del Object.attrib['LayerGUID']
            Write_to_LYR('LE_AIPoints', Object, NameLevel)
    print('- The processing of the files extracted by [CryDumper] has been completed.')

try:
    if not os.path.exists('level.pak') or not os.path.exists('terraintexture.pak'):
        raise ValueError('The [level.pak] or [terraintexture.pak] archives were not found. Check if these files are in the directory.')
    print('The program execution process:')
    with zipfile.ZipFile('level.pak') as zf:
        for file in zf.namelist():
            if file.startswith('brush/'):
                extract_path = os.path.join(file)
                os.makedirs(os.path.dirname(extract_path), exist_ok=True)
                with open(extract_path, 'wb') as f:
                    f.write(zf.read(file))
        print('- Extracted folder: [brush]')
        zf.extract('mission_mission0.xml')
        print('- The file was extracted: [mission_mission0.xml]')
        zf.extract('moviedata.xml')
        print('- The file was extracted: [moviedata.xml]')
        zf.extract('leveldata.xml')
        print('- The file was extracted: [leveldata.xml]')
        zf.extract('leveldataaction.xml')
        print('- The file was extracted: [leveldataaction.xml]')
    Mission_Mission0 = ET.parse('mission_mission0.xml').getroot()
    print('- The file was uploaded to the cache: [mission_mission0.xml]')
    MovieData = ET.parse('moviedata.xml').getroot()
    os.remove('moviedata.xml')
    print('- The file was uploaded to the cache and deleted: [moviedata.xml]')
    LevelData = ET.parse('leveldata.xml').getroot()
    print('- The file was uploaded to the cache: [leveldata.xml]')
    LevelInfo = LevelData.find('LevelInfo')
    LevelDataAction = ET.parse('leveldataaction.xml').getroot()
    os.remove('leveldataaction.xml')
    print('- The file was uploaded to the cache and deleted: [leveldataaction.xml]')
    if os.path.exists('ai_spawners_config.xml') is not None:
        AI_Spawners_Config = ET.parse('ai_spawners_config.xml').getroot()
        AI_Spawners_Presets = AI_Spawners_Config.findall('preset')
    else:
        raise ValueError('The file [ai_spawners_config.xml] not found. Check its presence in the directory.')
    NameLevel = LevelInfo.get('Name')
    print(f'- Level Name: [{NameLevel}]')
    if not os.path.isdir(NameLevel):
        Folders = [NameLevel, f'{NameLevel}\\Setting', f'{NameLevel}\\Setting\\Layers', f'{NameLevel}\\Setting\\TOD_and_Lighting', f'{NameLevel}\\Setting\\Terrain', f'{NameLevel}\\Setting\\Vegetation']
        for Folder in Folders:
            os.mkdir(Folder)
            print(f'- A new directory has been created: [{Folder}]')
    try:
        shutil.move('brush', f'{NameLevel}\\brush')
    except:
        None
    move('mission_mission0.xml', f'{NameLevel}\\Setting\\')
    move('leveldata.xml', f'{NameLevel}\\Setting\\')
    move('level.pak', f'{NameLevel}\\')
    move('terraintexture.pak', f'{NameLevel}\\')
    print(f'- Folder [brush], as well as files [level.pak], [terraintexture.pak], [mission_mission0.xml] and [leveldata.xml] were moved to the created level folder.')
    GUID_Cache = Cache_the_GUID(Mission_Mission0)
    print('- The process of extracting [.lyr] level files has begun. The duration of the process depends on the size of the level...')
    Layers = ['LE_AIPoints', 'LE_Unknown_Layer', 'LE_Decals', 'LE_Occluders', 'LE_VisAreas', 'LE_Portals', 'LE_SequenceObjects', 'LE_Others']
    Entities = []
    Objects = []
    Entity_Library = []
    Particles_Library = []
    GameTokens_Library = []
    for Entity in Mission_Mission0.findall('Objects/Entity'):
        Entities.append(Entity)
        Layer = Entity.get('Layer')
        if Layer not in Layers and Layer is not None:
            Layers.append(Layer)
    for Object in Mission_Mission0.findall('Objects/Object'):
        Objects.append(Object)
        Layer = Object.get('Layer')
        if Layer not in Layers and Layer is not None:
            Layers.append(Layer)
    for LevelDataLayer in LevelData.findall('Layers/Layer'):
        Layer = LevelDataLayer.get('Name')
        if Layer not in Layers and Layer is not None and Layer != "":
            Layers.append(Layer)
        Layer = LevelDataLayer.get('Parent')
        if Layer not in Layers and Layer is not None and Layer != "":
            Layers.append(Layer)
    Layers.sort()
    for Layer in Layers:
        Create_LYR(Layer, NameLevel)
    Processing_the_Entities_Array(Entities, AI_Spawners_Presets, NameLevel)
    Processing_the_Objects_Array(Objects, NameLevel)
    print('- The extraction process of [.lyr] level files is completed.')
    Extract_ToD(Mission_Mission0, NameLevel)
    Extract_LightSettings(Mission_Mission0, NameLevel)
    Create_File_TerrainLayerSettings_lay(LevelData, NameLevel)
    Extract_Library(Entity_Library, Particles_Library, GameTokens_Library, LevelData, LevelDataAction, NameLevel)
    if not os.path.isdir('NUX_MOD_SDK'):
        os.mkdir('NUX_MOD_SDK')
    what_NUX = int(input('\nIf you need to extract [Brush], [Road], [WaterVolume], [Vegetation] and [Terrain Block], then transfer all the [.lyr], [.veg]  and [.trb] files that [NUX_MOD_SDK] extracted to the appropriate folder and enter [1], otherwise [0].\nYour choice: '))
    if what_NUX == 1:
        Processing_of_NUX_MOD_SDK_Layers(LevelData, NameLevel, Layers)
    if not os.path.isdir('CryDumper'):
        os.mkdir('CryDumper')
    what_CryDumper = int(input('\nIf you need to extract [AIPoint], then transfer the [ai_points_dump.lyr] file that extracted [CryDumper] to the appropriate folder and enter [1], otherwise [0]. Your choice: '))
    if what_CryDumper == 1:
        Processing_of_CryDumper_Layer(NameLevel)
    input('\nThe program has been successfully completed, you can close the program by simply pressing the [Enter] key...')
except Exception as e:
    e = str(e)
    if e == "[Errno 2] No such file or directory: 'level.pak'":
        input('Error: The [level.pak] archive was not found. Check if this file is in the directory.')
    elif e == "Bad magic number for central directory":
        input('Error: The [level.pak] archive has not been decrypted. Decrypt the archive and try again.')
    else:
        input(f'Error: {e}')

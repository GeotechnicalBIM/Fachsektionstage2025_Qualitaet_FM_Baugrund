
import unittest
from collections import Counter

import os
import re
import ifcopenshell
from ifcopenshell.api import run
import ifcopenshell.util.element
import ifcopenshell.util.selector

import numpy as np
from scipy.spatial import Delaunay
from scipy.interpolate import griddata, LinearNDInterpolator

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(dir_path)
fp = parent_path+"/project_data/script_output_4x3_with_errors.ifc"
model = ifcopenshell.open(fp)


class TestBoreholes(unittest.TestCase):
    def test_ifcborehole_has_pset_ifcboreholecommon(self):
        """I.	Jedes Objekt der Klasse IfcBorehole verfügt über das PropertySet IfcBoreholeCommon."""
        elems = model.by_type("IfcBorehole")
        
        for elem in elems:
            with self.subTest(elem=elem):
                self.assertTrue("Pset_BoreholeCommon" in ifcopenshell.util.element.get_psets(elem).keys())
   

    def test_ifcborehole_is_in_ifcsite(self):
        """II.	Jedes IfcBorehole ist einer IfcSite zugeordnet."""
        elems = model.by_type("IfcBorehole")

        for elem in elems:
            container = ifcopenshell.util.element.get_container(elem)
            with self.subTest(elem=elem):
                if container: # To have a Fail instead of an error.
                    self.assertTrue(container.is_a("IfcSite"))
                else:
                    self.assertIsNotNone(container, f"Das Borehole {elem} ist keinem Container zugeordnet")
        

    def test_relationship_ifcgeotechnicalstratum_ifcborehole(self):
        """III. Sämtliche Objekte der Klasse IfcGeotechnicalStratum mit dem benutzerdefinierten ObjectType „ANSPRACHEBEREICH” sind Teil eines IfcBoreholes. Das Verhältnis Ganzes-Teil wird über IfcRelAggregates beschrieben. """
        # Filtern der Elemente
        elems = model.by_type("IfcGeotechnicalStratum")
        elems = [i for i in elems if i.ObjectType == "ANSPRACHEBEREICH"]
        
        # Alternativ unter Nutzung der Query Syntax
        elems = ifcopenshell.util.selector.filter_elements(model, "IfcGeotechnicalStratum, ObjectType=ANSPRACHEBEREICH")

        # Für jedes Element: Prüfen der Anforderung
        for elem in elems:
            with self.subTest(elem=elem):
                self.assertTrue(any((i.RelatingObject.is_a("IfcBorehole") and i.is_a("IfcRelAggregates")) for i in elem.Decomposes))
                #print(elem.Name, any((i.RelatingObject.is_a("IfcBorehole") and i.is_a("IfcRelAggregates")) for i in elem.Decomposes))
    
    
    def test_namingconvention_ifcborehole(self):
        """IV.	Die Namen der IfcBoreholes entsprechen folgender Namenskonvention: Die ersten drei stellen sind „bh_“ gefolgt von drei Ziffern."""
        elems = model.by_type("IfcBorehole")

        for elem in elems:
            with self.subTest(elem=elem):
                self.assertRegex(elem.Name, r'^bh_\d{3}$')


    def test_uniquenames_ifcbores(self):
        """V.	Die Namen der IfcBoreholes sind einzigartig."""
        # Nur prüfen, ob die Namen einzigartig sind
        # self.assertTrue(len([i.Name for i in model.by_type("IfcBorehole")]) == len(list(set([i.Name for i in model.by_type("IfcBorehole")]))))
        
        # Alternativ feingranularer
        elems = model.by_type("IfcBorehole")
        # Alternativ 
        counter = Counter([i.Name for i in model.by_type("IfcBorehole")])
        for elem in elems:
            with self.subTest(elem=elem):
                self.assertEqual(counter[elem.Name], 1, f"Name {elem.Name} kommt {counter[elem.Name]} mal vor.")



    def test_namingconvention_ansprachebereiche(self):
        """VI.	Die Namen der Ansprachebereiche entsprechen dem der zugehörigen IfcBoreholes, folgt von einem Unterstrich und drei Ziffern."""
        elems = model.by_type("IfcGeotechnicalStratum")
        elems = [i for i in elems if i.ObjectType=="ANSPRACHEBEREICH"]
        for elem in elems:
            with self.subTest(elem=elem):
                name = elem.Name
                if not elem.Decomposes:
                    self.assertIsNotNone(None, "No parent borehole found")
                if not any((i.RelatingObject.is_a("IfcBorehole") and i.is_a("IfcRelAggregates")) for i in elem.Decomposes):
                    self.assertIsNotNone(None, "No parent borehole found")
                for i in elem.Decomposes:
                    if (i.RelatingObject.is_a("IfcBorehole") and i.is_a("IfcRelAggregates")):
                        bh_name = i.RelatingObject.Name
                        self.assertRegex(elem.Name, fr'^{re.escape(bh_name)}_\d{{3}}$', "X"*100)
    


    def test_distances_ifcboreholes(self):
        """VII. Die Abstände der Bohrungen entsprechen den Empfehlungen aus Eurocode 7."""
        pass

    def test_ansprachebereich_geometry(self):
        """VIII.	Jeder Ansprachebereich wird als zylindrische Geometrie mit einem Durchmesser von einem Meter geometrisch repräsentiert."""

        elems = model.by_type("IfcBorehole")
        for elem in elems:
            with self.subTest(elem=elem):
                parts = elem.IsDecomposedBy
                if not parts:
                    continue
                for j in parts:
                    stratums = j.RelatedObjects
                    for k in stratums:
                        representations = k.Representation.Representations
                        representation = [i for i in representations if i.ContextOfItems.ContextIdentifier=="Body"][0]

                        self.assertEqual(representation.RepresentationType, "SweptSolid")
                        
                        if len(representation.Items)!=1:
                            self.assertEqual(elem, "Only one representation per Ansprachebereich expected")
                        else:
                            item = representation.Items[0]
                            sweptarea = item.SweptArea
                            if sweptarea.is_a("IfcCircleProfileDef"):
                                self.assertNotEqual(sweptarea.Radius, 1.0)
                            else:
                                self.assertTrue(sweptarea.is_a("IfcCircleProfileDef"))


    def test_abweichung_ansatzpunkt_dgm(self):
        """IX.	Die Abweichung des Ansatzpunkts einer Bohrung zum Digitalen Geländemodell darf maximal 50 cm betragen."""
        # Hinweis: Annahmen zur geometrischen Durchbildung bestehen
        # Get topography from the IFC Model
        topograhy = model.by_type("IfcGeographicElement")
        topograhy = [i for i in topograhy if i.PredefinedType=="TERRAIN"][0]
        rep = topograhy.Representation.Representations[0].Items[0]
        topograhy_coords = rep.Coordinates.CoordList
        topograhy_coords_2d = [[i[0], i[1]] for i in topograhy_coords]

        
        elems = model.by_type("IfcBorehole")

        for elem in elems:
            with self.subTest(elem=elem):
                parts = elem.IsDecomposedBy
                points_per_borehole = []
                if not parts:
                    continue
                for j in parts:
                    stratums = j.RelatedObjects
                    for k in stratums:
                        placement = k.ObjectPlacement
                        rel_to = placement.PlacementRelTo
                        c1 = placement.PlacementRelTo.RelativePlacement.Location.Coordinates
                        c2 = placement.RelativePlacement.Location.Coordinates
                        c3 = (c1[0]+c2[0], c1[1]+c2[1], c1[2]+c2[2])  
                        representations = k.Representation.Representations
                        representation = [i for i in representations if i.ContextOfItems.ContextIdentifier=="Body"][0]

                        if len(representation.Items)!=1:
                            raise ValueError(f"To many geometries assigned. Expected 1, got {len(representation.Items)}")
                        geom = representation.Items[0]

                        c4 = (c3[0] + geom.ExtrudedDirection.DirectionRatios[0] * geom.Depth,
                            c3[1] + geom.ExtrudedDirection.DirectionRatios[1] * geom.Depth,
                            c3[2] + geom.ExtrudedDirection.DirectionRatios[2] * geom.Depth)

                        if not geom.is_a("IfcExtrudedAreaSolid"):
                            raise ValueError(f"Expected an IfcExtrudedAreaSolid")
                        position = geom.Position.Location.Coordinates
                        c5 = (c4[0]+position[0], c4[1]+position[1], c4[2]+position[2])
                        points_per_borehole.append(c5)
                ansatzpunkt = sorted(points_per_borehole, key = lambda x : x[2], reverse=True)[0]

                # Using the actual topography.
                interpolator = LinearNDInterpolator(topograhy_coords_2d, [i[2] for i in topograhy_coords])
                z_val_new = interpolator(ansatzpunkt[0],ansatzpunkt[1])
                delta = np.abs(ansatzpunkt[2] - z_val_new)

                self.assertLessEqual(delta, 0.5)




class TestSolidStratum(unittest.TestCase):   
    
    def test_bounds_cohesion(self):
        """IX.	Werte für die CohesionBehaviour im Propertyset Pset_SolidStratumCapacity liegen im Intervall zwischen 0 und 1000 kN/m²."""
        elems = model.by_type("IfcSimpleProperty")
        elems = [i for i in elems if i.Name=="CohesionBehaviour"]
        elems = [i for i in elems if any(j.Name=="Pset_SolidStratumCapacity" for j in i.PartOfPset)]

        for elem in elems:
            with self.subTest(elem=elem):
                value = elem.NominalValue.wrappedValue
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 1000)

    def test_reibungswinkel_sand(self):
        """X.	Wird ein Reibungswinkel für ein Element mit dem Material „Sand“ angegeben, so liegt er zwischen 27,5° und 37,5°."""
        pass

    def test_material_color_DIN4023(self):
        """XI.	Die Farben der Materialien, die für die Bau-grundschichten genutzt werden, entspre-chen den Vorgaben aus DIN 4023."""
        pass

    def test_unit_(self):
        """XII"""
        pass

class TestIFCGeneral(unittest.TestCase):   
    
    def test_nominal_values_in_bounds(self):
        """XIII.	Die Nominalwerte sämtlicher Eigenschaften mit Grenzwerten müssen innerhalb dieser Grenzen liegen"""
        pass

    def test_file_size(self):
        """XIV.	Die Dateigröße darf 10 MB nicht überschreiten."""
        pass


if __name__ == '__main__':
    unittest.main(verbosity=1)
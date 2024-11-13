
import unittest
from collections import Counter

import os
import ifcopenshell
from ifcopenshell.api import run
import ifcopenshell.util.element
import ifcopenshell.util.selector

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
        pass

    def test_distances_ifcboreholes(self):
        """VII. Die Abstände der Bohrungen entsprechen den Empfehlungen aus Eurocode 7."""
        pass

    def test_ansprachebereich_geometry(self):
        """VIII.	Jeder Ansprachebereich wird als zylindrische Geometrie mit einem Durchmesser von einem Meter geometrisch repräsentiert."""
        pass


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
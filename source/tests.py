
import unittest

import os
import ifcopenshell
from ifcopenshell.api import run
import ifcopenshell.util.element
import ifcopenshell.util.selector

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(dir_path)
fp = parent_path+"/project_data/script_output_4x3.ifc"
model = ifcopenshell.open(fp)


class TestBoreholes(unittest.TestCase):
    def test_Modellaufbau_Borehole_GeotechnicalStratum(self):
        """Sämtliche Objekte der Klasse IfcGeotechnicalStratum mit dem benutzerdefinierten ObjectType „ANSPRACHEBEREICH” sind Teil eines IfcBoreholes. Das Verhältnis Ganzes-Teil wird über IfcRelAggregates beschrieben. """
        # Filtern der Elemente
        elems = model.by_type("IfcGeotechnicalStratum")
        elems = [i for i in elems if i.ObjectType == "ANSPRACHEBEREICH"]
        
        # Alternativ unter Nutzung der Query Syntax
        elems = ifcopenshell.util.selector.filter_elements(model, "IfcGeotechnicalStratum, ObjectType=ANSPRACHEBEREICH")

        # Für jedes Element: Prüfen der Anforderung
        for elem in elems:
            with self.subTest(elem=elem):
                self.assertTrue(any((i.RelatingObject.is_a("IfcBorehole") and i.is_a("IfcRelAggregates")) for i in elem.Decomposes))
    
    
    def test_WerteBereich_Kohaesion(self):
        """
        Prüft, ob die Eigenschaft CohesionBehaviour im Pset_SolidStratumCapacity in einem Wertebereich liegt
        """
        elems = model.by_type("IfcSimpleProperty")
        elems = [i for i in elems if i.Name=="CohesionBehaviour"]
        elems = [i for i in elems if any(j.Name=="Pset_SolidStratumCapacity" for j in i.PartOfPset)]

        for elem in elems:
            with self.subTest(elem=elem):
                value = elem.NominalValue.wrappedValue
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 1000)



class TestStringMethods(unittest.TestCase):
    def test_upper(self):
        tests = [
            ('foo', 'FOO'),
            ('too', 'TOO'),
            ('poo', 'POO'),
        ]
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(value.upper(), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
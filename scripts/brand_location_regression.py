"""No-network regression checks for Malaysian identity and location handling."""
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
ref=load("ref", "backend/medicine_card/refdata.py")
directory=load("directory", "backend/my_return_plan/directory.py")
safety=load("safety", "backend/medicine_card/patient_safety.py")
SEARCH='<table id="searchTable"><tr><td>1</td><td>MAL19970269ARZ</td><td>NORVASC TABLET 5MG</td></tr><tr><td>2</td><td>MAL19970268ARZ</td><td>NORVASC TABLET 10MG</td></tr></table>'
DETAIL='MAL19970269ARZ <table id="tab1"><tr><td>No</td><td>Active Ingredient</td></tr><tr><td>1</td><td>AMLODIPINE BESYLATE</td></tr></table>'
class Regressions(unittest.TestCase):
    def test_brand_only_extracted(self): self.assertEqual(safety.candidate_names("Panadol"),["Panadol"])
    def test_full_name_preserved(self): self.assertEqual(safety.candidate_names("NORVASC TABLET 5MG. Take 1 tablet daily."),["NORVASC TABLET 5MG"])
    def test_directions_not_names(self): self.assertEqual(safety.candidate_names("Take 1 tablet", "Not sure", "Draft only"),[])
    def test_brand_variants_not_selected(self):
        with patch.object(ref,"_quest_read",return_value=SEARCH): result=ref._npra("NORVASC")
        self.assertEqual(result["status"],"ambiguous");self.assertEqual(result["ingredients"],[]);self.assertEqual(len(result["candidates"]),2)
    def test_exact_product_with_source(self):
        with patch.object(ref,"_quest_read",side_effect=[SEARCH,"detail.php?type=product&id=MAL19970269A",DETAIL]): result=ref._npra("NORVASC TABLET 5MG")
        self.assertEqual(result["status"],"verified");self.assertEqual(result["ingredients"],["AMLODIPINE BESYLATE"]);self.assertTrue(result["sources"][0]["url"].startswith(ref._QUEST))
    def test_strength_without_form_remains_ambiguous(self):
        with patch.object(ref,"_quest_read",side_effect=['<table id="searchTable"></table>',SEARCH]): result=ref._npra("NORVASC 5MG")
        self.assertEqual(result["status"],"ambiguous");self.assertEqual(result["ingredients"],[])
    def test_missing_ingredient_not_identified(self):
        with patch.object(ref,"_quest_read",side_effect=[SEARCH,"detail.php?type=product&id=MAL19970269A","MAL19970269ARZ"]): result=ref._npra("NORVASC TABLET 5MG")
        self.assertEqual(result["status"],"unverified")
    def test_outage_not_identified(self):
        with patch.object(ref,"_quest_read",side_effect=TimeoutError): result=ref._npra("NORVASC")
        self.assertEqual(result["status"],"unverified")
    def test_external_detail_refused(self):
        with patch.object(ref,"_quest_read",side_effect=[SEARCH,"https://example.org/"]): result=ref._npra("NORVASC TABLET 5MG")
        self.assertEqual(result["status"],"unverified")
    def test_changed_format_refused(self):
        with patch.object(ref,"_quest_read",return_value="CAPTCHA or changed markup"): result=ref._npra("NORVASC")
        self.assertEqual(result["status"],"unverified")
    def test_nearest_matches_minimum_source_distance(self):
        origin,points=directory.nearest("50480 Kuala Lumpur")
        self.assertEqual(len(points),3)
        self.assertAlmostEqual(points[0]["distance_km"],min(directory.distance(origin,p) for p in directory.DIRECTORY["locations"]))
        self.assertTrue(all(any(p["name"]==source["name"] and p["latitude"]==source["latitude"] for source in directory.DIRECTORY["locations"]) for p in points))
    def test_town_lookup(self): self.assertEqual(len(directory.nearest("Petaling Jaya")[1]),3)
    def test_invalid_and_conflicting_locations(self):
        for text in ("", "00000", "Klang 00000", "50480 Johor Bahru", "50480 80200", "Malaysia", "<script>alert(1)</script>"):
            with self.subTest(text=text): self.assertEqual(directory.nearest(text),(None,[]))
    def test_east_malaysia_postcode(self):
        row=next(r for r in directory.POSTAL["places"] if r["state"]=="Sabah")
        self.assertIsNotNone(directory.locate(row["postcode"]))
if __name__=="__main__": unittest.main()

"""Offline tests for the approved elderly-friendly Return Plan frame."""
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend/my_return_plan"))
import app, directory
class FrameTests(unittest.TestCase):
    def result(self, details="Paracetamol 500 mg, 20 tablets, expired", location="SS2 PJ", language="English", **extras):
        return "".join(app.generate(dict(return_item_details=details,your_location=location,preferred_language=language,**extras)))
    def test_approved_frame(self):
        text=self.result()
        self.assertIn("## 💊 Your return",text)
        self.assertIn("- **Medicine:** Paracetamol 500 mg.",text)
        self.assertIn("- **Amount:** 20 tablets.",text)
        self.assertIn("- **Reason:** Expired — **do not take them**.",text)
        prepare=text.split("## 📦 Prepare and keep safely\n")[1].split("## 📍")[0]
        self.assertEqual(sum(line.startswith("- ") for line in prepare.splitlines()),4)
        self.assertIn("**Health Lane Family Pharmacy SS2**",text)
        self.assertEqual(text.count("google.com/maps/dir/"),1)
        self.assertNotIn("Check the label",text)
    def test_unusual_amount_is_not_corrected(self):
        text=self.result("Paracetamol 5000 mg, 20 tablets, expired")
        self.assertIn("Paracetamol 5000 mg",text)
        self.assertIn("**Check the label:**",text)
        self.assertIn("**seek urgent medical help**",text)
        self.assertNotIn("Paracetamol 500 mg",text)
    def test_small_strength_ratio_not_warned(self):
        self.assertFalse(app._unusual_paracetamol("Paracetamol 250 mg/5 mL suspension"))
    def test_liquids(self):
        text=self.result("Medicine: Panadol suspension 250 mg/5 mL\nAmount: 100 mL\nReason: expired")
        self.assertIn("**Amount:** 100 mL",text)
        self.assertIn("close liquid bottles tightly",text)
        self.assertNotIn("100 tablets",text)
    def test_special_items_four_bullets(self):
        text=self.result("Needles and inhaler, expired")
        prepare=text.split("## 📦 Prepare and keep safely\n")[1].split("## 📍")[0]
        self.assertEqual(sum(line.startswith("- ") for line in prepare.splitlines()),4)
        self.assertIn("**suitable sharps container**",text)
        self.assertIn("Do not puncture inhalers",text)
    def test_missing_fields_not_invented(self):
        text=self.result("")
        self.assertIn("**Medicine:** Not provided",text)
        self.assertIn("**Amount:** Not provided",text)
        self.assertIn("**Reason:** Not provided",text)
        self.assertIn("**Check with your pharmacist**",text)
    def test_negated_expiry_not_reported(self):
        self.assertIsNone(app._return_details("Paracetamol 500 mg, 20 tablets, not expired")["reason"])
    def test_conflicting_reason_not_selected(self):
        self.assertIsNone(app._return_details("Medicine expired or damaged, not sure")["reason"])
    def test_photo_not_identified(self):
        text=self.result("",file_data="blurred")
        self.assertIn("No medicine has been identified from the photo",text)
        self.assertIn("**Medicine:** Not provided",text)
    def test_area_match_does_not_include_ss21(self):
        points=directory.listed_in_area("SS2 PJ")
        self.assertEqual(len(points),3)
        self.assertTrue(all("SS2" in p["name"].replace(" ","") for p in points))
        self.assertEqual(directory.listed_in_area("SS2 PJ 80200"),[])
    def test_wrong_location_does_not_guess(self):
        text=self.result(location="SS2 Johor Bahru")
        self.assertNotIn("google.com/maps/dir/",text)
        self.assertIn("town or postcode",text)
    def test_malay_chinese_frame(self):
        for language in ("Bahasa Melayu","中文"):
            with self.subTest(language=language):
                text=self.result(language=language)
                self.assertEqual(text.count("## "),3)
                self.assertIn("## 💊 "+app.FRAME[language]["return"],text)
                self.assertNotIn("Prepare and keep safely",text)
                self.assertIn(app.FRAME[language]["call"],text)
    def test_markup_in_input_is_data(self):
        text=self.result("<script>alert(1)</script> [medicine](https://evil.example), 20 tablets, expired")
        self.assertNotIn("<script>",text)
        self.assertNotIn("](https://evil.example)",text)
    def test_postcode_selection_has_uncertainty(self):
        text=self.result(location="50480 Kuala Lumpur")
        self.assertIn("approximate town/postcode coordinates",text)
        self.assertEqual(text.count("google.com/maps/dir/"),1)
if __name__=="__main__": unittest.main()

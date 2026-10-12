"""Offline evidence/prompt/stream regressions. No clinical approval is implied."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from patient_regression import load, missing_reference_files

class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.summary,self.safety,self.model,self.names=load('my_medicine_summary')
        self.refs=sys.modules['clinical_refs']
    def verified(self,ingredients,query='Atorvastatin 20 mg tablets'):
        return {'status':'verified','query':query,'ingredients':ingredients,'matched_name':query,'sources':[]}
    def page(self,url='https://www.nhs.uk/medicines/atorvastatin/'):
        return {'url':url,'title':'Atorvastatin','text':'Synthetic test evidence. Limit large amounts of grapefruit juice. Alcohol can increase liver-related side effects.','country':'UK','population':'adults','retrieved_at':'test'}
    def test_preflight_reports_all_missing_reference_paths(self):
        with patch('pathlib.Path.is_file',return_value=False): missing=missing_reference_files()
        self.assertEqual(len(missing),4)
        self.assertIn('backend/medicine_card/clinical_refs.py',missing)
        self.assertIn('backend/my_medicine_summary/clinical_catalog.json',missing)
    def test_four_sections_and_no_repeated_sections(self):
        prompt=self.summary.SYSTEM_PROMPT
        headings=['# 💊 Your Medicine Summary','## 👀 Watch Out For','## 🍽️ Food and Drink','## ❓ Ask Your Pharmacist','## 📚 Sources']
        self.assertEqual([prompt.index(h) for h in headings],sorted(prompt.index(h) for h in headings))
        self.assertIn('Do NOT add Your Instructions, What It Is For',prompt)
        self.assertIn('At most three',prompt)
    def test_actual_article_text_in_context(self):
        v=self.verified(['atorvastatin']);page=self.page()
        records=[{'status':'retrieved','query':v['query'],'pages':[page]}]
        with patch.object(self.summary,'prepare',return_value=([v],records)):
            text=self.summary.build_messages({'medicine_details':v['query']})[0]['content'][0]['text']
        self.assertIn(page['text'],text)
        self.assertIn('CLINICAL EVIDENCE',text)
        self.assertIn('NOT no allergies',text)
    def test_combination_must_match_complete_ingredient_set(self):
        self.assertIsNone(self.refs._entry(self.verified(['paracetamol','caffeine'])))
        self.assertIsNotNone(self.refs._entry(self.verified(['AMOXICILLIN TRIHYDRATE','POTASSIUM CLAVULANATE'])))
        self.assertIsNotNone(self.refs._entry(self.verified(['PARACETAMOL','CODEINE PHOSPHATE'])))
    def test_brand_salt_identity_maps_to_exact_ingredient(self):
        self.assertIsNotNone(self.refs._entry(self.verified(['AMLODIPINE BESYLATE'],'NORVASC TABLET 5MG')))
    def test_ambiguous_identity_never_fetches(self):
        with patch.object(self.refs,'_fetch') as fetch:
            records=self.refs.retrieve([{'status':'ambiguous','query':'Panadol','ingredients':['paracetamol']}])
        fetch.assert_not_called();self.assertEqual(records[0]['pages'],[])
    def test_route_and_population_mismatch_do_not_fetch(self):
        with patch.object(self.refs,'_fetch') as fetch:
            a=self.refs.retrieve([self.verified(['paracetamol'],'Paracetamol 500 mg suppositories')],'Paracetamol 500 mg suppositories','Adult')
            b=self.refs.retrieve([self.verified(['paracetamol'])],age='Child 8 years')
        fetch.assert_not_called();self.assertEqual(a[0]['pages'],[]);self.assertEqual(b[0]['pages'],[])
    def test_unknown_scope_is_not_silently_assumed(self):
        with patch.object(self.refs,'_fetch',return_value=self.page()):
            records=self.refs.retrieve([self.verified(['atorvastatin'],'Atorvastatin 20 mg')],'Atorvastatin 20 mg')
        self.assertEqual(records[0]['scope']['form'],'Not provided')
        self.assertEqual(records[0]['scope']['population'],'Not provided')
    def test_source_outage_has_no_page_or_stale_fallback(self):
        with patch.object(self.refs,'_fetch',side_effect=TimeoutError):
            records=self.refs.retrieve([self.verified(['atorvastatin'])])
        self.assertEqual(records[0]['status'],'unavailable');self.assertEqual(records[0]['pages'],[])
    def test_citation_gate_handles_split_links(self):
        good=self.page()['url'];gate=self.refs.CitationGate({good})
        chunks=['Advice [real]('+good[:25],good[25:]+')\n','[Fake](https://invent','ed.example/)\n','https://invented.example/page\n']
        result=''.join(part for c in chunks for part in gate.feed(c))+''.join(gate.finish())
        self.assertIn(good,result);self.assertNotIn('invented.example',result);self.assertNotIn('[Fake]',result)
    def test_model_stream_and_config_retained(self):
        seen={}
        def stream(**kwargs):
            seen.update(kwargs)
            return {'stream':[{'contentBlockDelta':{'delta':{'text':c}}} for c in ['# 💊 Your Medicine Summary\n','## 👀 Watch Out For\n','[fake](https://invented.example/)\n']]}
        self.model.converse_stream=stream
        text=''.join(self.summary.generate({'medicine_details':'Atorvastatin 20 mg tablets'}))
        self.assertEqual(seen['inferenceConfig'],{'temperature':0,'maxTokens':2000})
        self.assertEqual(seen['modelId'],self.summary.MODEL_ID)
        self.assertNotIn('invented.example',text)
        self.assertTrue(text.endswith(self.summary.ENDINGS['English']))
    def test_truncated_stream_reports_incomplete(self):
        self.model.converse_stream=lambda **kwargs: {'stream':[{'contentBlockDelta':{'delta':{'text':'Partial answer\n'}}},{'messageStop':{'stopReason':'max_tokens'}}]}
        text=''.join(self.summary.generate({'medicine_details':'Metformin 500 mg tablets'}))
        self.assertIn('No complete result was saved',text)
        self.assertFalse(text.endswith(self.summary.ENDINGS['English']))
    def test_more_than_four_medicines_are_processed(self):
        raw='\n'.join(f'MedicineName{i} 20 mg tablets' for i in range(6))
        self.summary.build_messages({'medicine_details':raw})
        self.assertEqual(len(self.names),6)
    def test_language_and_closing_line(self):
        for language in ('English','Bahasa Melayu','中文'):
            text=''.join(self.summary.generate({'medicine_details':'Metformin 500 mg tablets','preferred_language':language}))
            self.assertTrue(text.endswith(self.summary.ENDINGS[language]))
            prompt=self.summary.build_messages({'medicine_details':'Metformin 500 mg tablets','preferred_language':language})[0]['content'][0]['text']
            self.assertIn('Preferred Language: '+language,prompt)
    def test_multiple_raw_labels_and_not_card_prose(self):
        self.summary.build_messages({'medicine_details':'Metformin 500 mg tablets\nAtorvastatin 20 mg tablets','other_medicines':'Unknown medicine','medicine_card':'Draf RxNorm 200 mg'})
        self.assertEqual(self.names,['Metformin 500 mg tablets','Atorvastatin 20 mg tablets'])
    def test_missing_unit_still_blocks_model(self):
        text=''.join(self.summary.generate({'medicine_details':'Metformin 500 mg. Take 5 daily.'}))
        self.assertIn('no unit',text);self.assertEqual(self.model.calls,0)
    def test_card_layout_and_origin_constraints_preserved(self):
        card,_,_,_=load('medicine_card')
        for text in ('🏷️ Name:','🧪 Active ingredient:','📏 Strength:','💉 Form:','💬 Plain words:','ℹ️ What it is for:','⚠️ Needs checking:'):
            self.assertIn(text,card.SYSTEM_PROMPT)
        self.assertIn('identify the instruction origin',card.SYSTEM_PROMPT)
        self.assertIn('requires exact-ingredient retrieved clinical text',card.SYSTEM_PROMPT)
    def test_conflict_and_as_needed_rules(self):
        card,_,_,_=load('medicine_card')
        for prompt in [card.SYSTEM_PROMPT,self.summary.SYSTEM_PROMPT]:
            self.assertIn('BEFORE',prompt);self.assertIn('as-needed',prompt);self.assertIn('500',prompt)
        body={'medicine_details':'Atenolol 500 mg tablets nightly','extract_from_photo':'Atenolol 50 mg tablets in the morning'}
        text=self.summary.build_messages(body)[0]['content'][0]['text']
        self.assertIn(body['medicine_details'],text);self.assertIn(body['extract_from_photo'],text)
    def test_dose_warning_requires_actual_label(self):
        self.assertEqual(list(self.refs.dose_alerts([], 'Atenolol 500 mg once daily at night','English')),[])
        page=self.page('https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=test');page['country']='US'
        text=''.join(self.refs.dose_alerts([{'pages':[page]}],'Atenolol 500 mg once daily at night','English'))
        self.assertIn('Atenolol 500 mg',text);self.assertNotIn('Atenolol 50 mg',text)
    def test_generic_identity_does_not_select_a_brand(self):
        spec=importlib.util.spec_from_file_location('identity_test',ROOT/'backend/my_medicine_summary/refdata.py')
        ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        good={'status':'verified','query':'atenolol','ingredients':['atenolol'],'sources':[]}
        with patch.object(ref,'_exact_ingredient',return_value=good),patch.object(ref,'_npra') as npra:
            result=ref.verify_medicine('Atenolol 500 mg tablets')
        npra.assert_not_called();self.assertEqual(result['ingredients'],['atenolol']);self.assertEqual(result['query'],'Atenolol 500 mg tablets')
    def test_generic_related_salts_are_not_combination_ingredients(self):
        spec=importlib.util.spec_from_file_location('identity_test',ROOT/'backend/my_medicine_summary/refdata.py')
        ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        good={'status':'verified','query':'atorvastatin','ingredients':['atorvastatin'],'sources':[]}
        with patch.object(ref,'_exact_ingredient',return_value=good): result=ref.verify_medicine('Atorvastatin 20 mg tablets')
        self.assertEqual(result['ingredients'],['atorvastatin'])
    def identity_module(self):
        spec=importlib.util.spec_from_file_location('identity_test',ROOT/'backend/my_medicine_summary/refdata.py')
        ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref);return ref
    def test_generic_outside_clinical_catalogue_accepted(self):
        ref=self.identity_module()
        with patch.object(ref,'_get_json',side_effect=[{'idGroup':{'rxnormId':['29046']}},{'properties':{'tty':'IN','name':'lisinopril','suppress':'N'}}]):
            result=ref._exact_ingredient('lisinopril')
        self.assertEqual(result['status'],'verified');self.assertEqual(result['ingredients'],['lisinopril'])
        self.assertIsNone(self.refs._entry(result))  # identity is independent of clinical coverage
    def test_chemical_salt_is_not_a_brand(self):
        ref=self.identity_module()
        with patch.object(ref,'_get_json',side_effect=[{'idGroup':{'rxnormId':['salt']}},{'properties':{'tty':'PIN','name':'metformin hydrochloride','suppress':'N'}}]):
            result=ref._exact_ingredient('metformin hydrochloride')
        self.assertEqual(result['ingredients'],['metformin hydrochloride'])
    def test_brand_cannot_use_us_generic_path(self):
        ref=self.identity_module()
        with patch.object(ref,'_get_json',side_effect=[{'idGroup':{'rxnormId':['brand']}},{'properties':{'tty':'BN','name':'Panadol','suppress':'N'}}]):
            self.assertIsNone(ref._exact_ingredient('Panadol'))
    def test_multiple_exact_concepts_not_auto_selected(self):
        ref=self.identity_module()
        with patch.object(ref,'_get_json',return_value={'idGroup':{'rxnormId':['1','2']}}):self.assertIsNone(ref._exact_ingredient('ambiguous'))
    def test_exact_search_never_fuzzy(self):
        ref=self.identity_module()
        with patch.object(ref,'_get_json',return_value={'idGroup':{}}) as read:
            self.assertIsNone(ref._exact_ingredient('atenlol'))
        self.assertIn('search=0',read.call_args.args[0])
    def test_mixed_named_strengths_not_truncated(self):
        ref=self.identity_module()
        text='Amoxicillin 500 mg / clavulanic acid 125 mg'
        self.assertEqual(ref._generic_query(text),text)
        self.assertEqual(ref._generic_query('Paracetamol 500 mg tablets'),'Paracetamol')
    def test_generic_combination_keeps_all_ingredients(self):
        ref=self.identity_module()
        with patch.object(ref,'_get_json',side_effect=[{'idGroup':{'rxnormId':['combo']}},{'properties':{'tty':'MIN','name':'amoxicillin / clavulanate','suppress':'N'}},{'relatedGroup':{'conceptGroup':[{'tty':'IN','conceptProperties':[{'name':'amoxicillin'},{'name':'clavulanate'}]}]}}]):
            result=ref._exact_ingredient('amoxicillin / clavulanate')
        self.assertEqual(result['ingredients'],['amoxicillin','clavulanate'])
    def test_misspelling_not_autocorrected_by_generic_layer(self):
        spec=importlib.util.spec_from_file_location('identity_test',ROOT/'backend/my_medicine_summary/refdata.py')
        ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        bad={'status':'unverified','query':'atenlol','ingredients':[],'sources':[],'note':'Unavailable'}
        with patch.object(ref,'_exact_ingredient',return_value=None) as nlm,patch.object(ref,'_npra',return_value=bad):
            result=ref.verify_medicine('Atenlol 500 mg')
        nlm.assert_called_once_with('Atenlol');self.assertEqual(result['status'],'unverified')
    def test_expired_reference_is_not_reused_when_fetch_fails(self):
        entry=next(e for e in self.refs.CATALOG['entries'] if e['ingredients']==['atorvastatin'])
        self.refs._CACHE[entry['url']]={'expires':0,'record':self.page()}
        with patch.object(self.refs.urllib.request,'build_opener',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):self.refs._fetch(entry)
    def test_article_parser_excludes_script_and_navigation(self):
        parser=self.refs.Article();parser.feed('<main id="maincontent"><h1>Atorvastatin</h1><p>Evidence</p><script>malicious()</script><nav>Menu</nav></main><footer>Footer</footer>')
        self.assertIn('Evidence',parser.text());self.assertNotIn('malicious',parser.text());self.assertNotIn('Menu',parser.text());self.assertNotIn('Footer',parser.text())
    def test_lasa_provenance_is_versioned(self):
        self.assertEqual(self.summary.LASA['source']['year'],2012)
        self.assertEqual(len(self.summary.LASA['source']['document_sha256']),64)
        self.assertIn('non-exhaustive',self.summary.LASA['source']['note'].lower())
if __name__=='__main__': unittest.main()

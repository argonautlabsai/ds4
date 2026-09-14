import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('summary',Path(__file__).resolve().parents[1]/'summarize.py')
summary=importlib.util.module_from_spec(spec);spec.loader.exec_module(summary)


class SummaryTests(unittest.TestCase):
    def report(self):
        rows=[]
        for pp,tgs,variants in [(512,[128,512],summary.LABELS),(2048,[60],['upstream','fork-plus2'])]:
            for tg in tgs:
                for variant in variants:
                    for rep in [1,2,3]:
                        base=10+rep;rate=base*(1.5 if variant=='fork-plus2' else 1)
                        rows.append({'variant':variant,'prompt_tokens':pp,'generated_tokens':tg,'repetition':rep,
                            'output_matches_upstream':True,
                            'result':dict.fromkeys(['generation_tok_s','steady_tok_s','prefill_tok_s','first_decode_step_ms'],rate),
                            'phase_analysis':{'decode':{'drives':{d:{'gb_s':1} for d in ['internal','Green','White']},'physical_gb_per_token':.3}}})
        return {'status':'complete','runs':rows}

    def test_paired_gain_and_full_range(self):
        result,_=summary.summarize(self.report())
        item=next(x for x in result if x['variant']=='fork-plus2' and x['generated_tokens']==512)
        self.assertEqual(item['generation_tok_s']['median'],18)
        self.assertEqual(item['generation_tok_s']['min'],16.5)
        self.assertEqual(item['generation_tok_s']['max'],19.5)
        self.assertEqual(item['paired_generation_gain_percent']['values'],[50,50,50])

    def test_incomplete_duplicate_and_wrong_output_refused(self):
        q=self.report();q['runs'].pop()
        with self.assertRaises(ValueError):summary.summarize(q)
        q=self.report();q['runs'][0]['repetition']=2
        with self.assertRaises(ValueError):summary.summarize(q)
        q=self.report();q['runs'][0]['output_matches_upstream']=False
        with self.assertRaises(ValueError):summary.summarize(q)


if __name__=='__main__':unittest.main()

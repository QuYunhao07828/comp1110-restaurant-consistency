"""Isolated return-import fixtures. No fixture is a student or study observation."""
import copy
import contextlib
import csv
from datetime import date, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
from zipfile import ZipFile

import import_assisted_returns as importer
import finalise_main_review as main_review


@contextlib.contextmanager
def fixture_directory():
    base=Path(__file__).resolve().parents[1]/'tmp'
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base,prefix='return-import-fixture-') as folder:
        if not Path(folder).resolve().is_relative_to(base.resolve()):
            raise ValueError('Temporary fixture escaped its intended workspace')
        yield Path(folder)


def fixtures():
    sample = [{"branch_id":f"B{i}", "name_en":f"ISOLATED FIXTURE {i}", "address_en":f"Unit {i}, Fixture Road",
               "address_zh":f"隔离样例{i}号铺", "district":"Fixture district", "pilot":False} for i in [1,2]]
    sources = {"OSM":{}, "Overture":{}}
    grid, tasks = {}, []
    for i, b in enumerate(sample, 1):
        for src in importer.SOURCES:
            rid = f"node/{100+i}" if src=="OSM" else f"00000000-0000-0000-0000-{i:012d}"
            sources[src][rid] = {"id":rid}
            note = {"branch_id":b["branch_id"], "source":src, "suggestion":"ISOLATED AI NOTE",
                    "selected_ids":[rid], "reason":"ISOLATED AI EVIDENCE; NOT A REAL REVIEW", "question":""}
            tasks.append(note)
            grid[(b["branch_id"],src)] = [b["branch_id"],b["name_en"],src,b["address_zh"],note["suggestion"],rid,note["reason"],"","","","","",""]
    original = {"rows":grid, "assistance_date":"2020-01-01"}
    returned = copy.deepcopy(original)
    for row in returned["rows"].values():
        row[8:12] = ["Confirmed", "ISOLATED FIXTURE REASON; NOT STUDENT EVIDENCE", "Fixture reviewer", "2020-01-02"]
    return sample, sources, original, returned, {"tasks":tasks}


def tiny_xlsx(path, grid, formula=False, bad_header=False, dimension=True):
    """Minimal temporary OOXML input for reader tests, not a delivered workbook."""
    cells = []
    def cell(ref,value,as_formula=False):
        if as_formula:
            return f'<c r="{ref}"><f>{escape(value)}</f></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
    cells.append('<row r="5">'+cell('H5',grid['assistance_date'])+'</row>')
    headers=list(importer.SHEET_HEADERS)
    if bad_header: headers[8]='Changed header'
    cells.append('<row r="7">'+''.join(cell(chr(65+i)+'7',v) for i,v in enumerate(headers))+'</row>')
    for n,row in enumerate(grid['rows'].values(),8):
        values=[cell(chr(65+i)+str(n),v,formula and n==8 and i==8) for i,v in enumerate(row)]
        cells.append(f'<row r="{n}">'+''.join(values)+'</row>')
    content='''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'''
    rels='''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    book='''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Main review" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    bookrels='''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'''
    with ZipFile(path,'w') as archive:
        archive.writestr('[Content_Types].xml',content)
        archive.writestr('_rels/.rels',rels)
        archive.writestr('xl/workbook.xml',book)
        archive.writestr('xl/_rels/workbook.xml.rels',bookrels)
        extent='<dimension ref="A1:M'+str(7+len(grid['rows']))+'"/>' if dimension else ''
        archive.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+extent+'<sheetData>'+''.join(cells)+'</sheetData></worksheet>')


class ReturnConversionTests(unittest.TestCase):
    def setUp(self):
        self.sample,self.sources,self.original,self.returned,self.triage=fixtures()
        self.key=('B1','OSM')

    def convert(self):
        return importer.convert(self.original,self.returned,self.triage,self.sample,self.sources)

    def test_complete_declarations_keep_ids_and_explicit_ai_flag(self):
        rows=self.convert()
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]['record_id'],'node/101')
        self.assertTrue(all(r['ai_assisted']=='true' and not r['pilot'] for r in rows))

    def test_blank_form_is_not_promoted(self):
        self.returned=copy.deepcopy(self.original)
        with self.assertRaisesRegex(ValueError,'human I-L'): self.convert()

    def test_prefilled_evidence_changes_are_rejected(self):
        for column in [1,3,5,6]:
            with self.subTest(column=column):
                old=self.returned['rows'][self.key][column]
                self.returned['rows'][self.key][column]='Changed'
                with self.assertRaisesRegex(ValueError,'A-H'): self.convert()
                self.returned['rows'][self.key][column]=old

    def test_multiple_ai_ids_need_explicit_selection(self):
        self.original['rows'][self.key][5]='node/101; node/999'
        self.returned['rows'][self.key][5]='node/101; node/999'
        self.triage['tasks'][0]['selected_ids']=['node/101','node/999']
        self.sources['OSM']['node/999']={'id':'node/999'}
        with self.assertRaisesRegex(ValueError,'one explicit ID'): self.convert()
        self.returned['rows'][self.key][9]='ID=node/999; ISOLATED SUPPLEMENTARY EVIDENCE'
        self.assertEqual(self.convert()[0]['record_id'],'node/999')

    def test_explicit_new_snapshot_id_can_replace_absent_suggestion(self):
        self.original['rows'][self.key][5]=''
        self.returned['rows'][self.key][5]=''
        self.triage['tasks'][0]['selected_ids']=[]
        with self.assertRaisesRegex(ValueError,'one explicit ID'): self.convert()
        self.sources['OSM']['node/999']={'id':'node/999'}
        self.returned['rows'][self.key][9]='ID=node/999; ISOLATED FULL SNAPSHOT SEARCH'
        self.assertEqual(self.convert()[0]['record_id'],'node/999')

    def test_foreign_source_and_duplicate_assignments_are_rejected(self):
        self.returned['rows'][self.key][9]='ID=00000000-0000-0000-0000-000000000001; FIXTURE'
        with self.assertRaisesRegex(ValueError,'declared source'): self.convert()
        self.returned['rows'][self.key][9]='ISOLATED FIXTURE EVIDENCE'
        self.returned['rows'][('B2','OSM')][9]='ID=node/101; FIXTURE DUPLICATE'
        with self.assertRaisesRegex(ValueError,'multiple branches'): self.convert()

    def test_review_date_cannot_predate_assistance_or_be_future(self):
        self.returned['rows'][self.key][11]='2019-12-31'
        with self.assertRaisesRegex(ValueError,'predate'): self.convert()
        self.returned['rows'][self.key][11]=(date.today()+timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'future'): self.convert()

    def test_uncertainty_does_not_select_ai_id(self):
        self.returned['rows'][self.key][8]='Uncertain'
        self.assertEqual(self.convert()[0]['record_id'],'')
        self.returned['rows'][self.key][9]='ID=node/101; FIXTURE TENTATIVE ONLY'
        self.assertEqual(self.convert()[0]['record_id'],'node/101')

    def test_nonconfirmation_clears_suggestion_but_cannot_select(self):
        self.returned['rows'][self.key][8]='No counterpart confirmed'
        self.assertEqual(self.convert()[0]['record_id'],'')
        self.returned['rows'][self.key][9]='ID=node/101; CONTRADICTORY FIXTURE'
        with self.assertRaisesRegex(ValueError,'cannot also select'): self.convert()

    def test_different_id_in_prose_is_not_guessed(self):
        self.returned['rows'][self.key][9]='ISOLATED FIXTURE discussed node/999'
        with self.assertRaisesRegex(ValueError,'another source ID'): self.convert()

    def test_incomplete_id_override_needs_reason(self):
        self.returned['rows'][self.key][9]='ID=node/101; '
        with self.assertRaises(ValueError): self.convert()

    def test_reference_cannot_be_another_filled_return(self):
        self.original['rows'][self.key][8]='Confirmed'
        with self.assertRaisesRegex(ValueError,'unfilled original'): self.convert()

    def test_missing_tasks_and_pilot_targets_are_rejected(self):
        del self.returned['rows'][self.key]
        with self.assertRaisesRegex(ValueError,'task IDs'): self.convert()
        self.returned=fixtures()[3]
        self.sample[0]['pilot']=True
        with self.assertRaisesRegex(ValueError,'non-pilot'): self.convert()


class WorkbookReaderTests(unittest.TestCase):
    def test_isolated_cli_writes_only_declarations_and_rejects_blank_or_changed_sources(self):
        sample,sources,original,returned,triage=fixtures()
        with fixture_directory() as folder:
            processed=folder/'data/processed'
            processed.mkdir(parents=True)
            files={'sample_100_enriched.json':sample, 'osm_records.json':list(sources['OSM'].values()),
                   'overture_records.json':list(sources['Overture'].values())}
            for name,value in files.items():
                (processed/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
            docs=folder/'docs'
            docs.mkdir()
            manifest={'files':[{'path':p.relative_to(folder).as_posix(),'sha256':importer.digest(p)} for p in processed.iterdir()]}
            (docs/'evidence_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            original_path,returned_path=folder/'original.xlsx',folder/'returned.xlsx'
            tiny_xlsx(original_path,original,dimension=False)
            tiny_xlsx(returned_path,returned,dimension=False)
            triage_path=folder/'triage.json'
            triage_path.write_text(json.dumps(triage),encoding='utf-8')
            out=folder/'converted_fixture'
            args=['program','--original',str(original_path),'--triage',str(triage_path),
                  '--returned',str(returned_path),'--output-dir',str(out)]
            with patch.object(importer,'ROOT',folder),patch.object(main_review,'ROOT',folder),patch('sys.argv',args),contextlib.redirect_stdout(io.StringIO()):
                importer.main()
            with (out/'nonpilot_review_declarations.csv').open(encoding='utf-8-sig',newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),4)
            self.assertTrue(all(r['ai_assisted']=='true' for r in rows))
            receipt=json.loads((out/'import_receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['independent_labels_created'],0)
            self.assertFalse(receipt['final_coverage_or_accuracy_created'])
            args[-1]=str(folder/'must_not_exist')
            tiny_xlsx(returned_path,original)
            with patch.object(importer,'ROOT',folder),patch.object(main_review,'ROOT',folder),patch('sys.argv',args):
                with self.assertRaisesRegex(ValueError,'Blank or incomplete'): importer.main()
            self.assertFalse(Path(args[-1]).exists())
            tiny_xlsx(returned_path,returned)
            (processed/'osm_records.json').write_text('[]',encoding='utf-8')
            with patch.object(importer,'ROOT',folder),patch.object(main_review,'ROOT',folder),patch('sys.argv',args):
                with self.assertRaisesRegex(ValueError,'Source fields differ'): importer.main()
            self.assertFalse(Path(args[-1]).exists())

    def test_actual_xlsx_reader_checks_headers_and_formulas(self):
        original=fixtures()[2]
        with fixture_directory() as folder:
            path=Path(folder)/'isolated.xlsx'
            tiny_xlsx(path,original)
            self.assertEqual(set(importer.read_grid(path)['rows']),set(original['rows']))
            tiny_xlsx(path,original,dimension=False)
            self.assertEqual(set(importer.read_grid(path)['rows']),set(original['rows']))
            tiny_xlsx(path,original,bad_header=True)
            with self.assertRaisesRegex(ValueError,'headers'): importer.read_grid(path)
            tiny_xlsx(path,fixtures()[3],formula=True)
            with self.assertRaisesRegex(ValueError,'not formulas'): importer.read_grid(path)

    def test_existing_output_is_refused_before_reading_inputs(self):
        with fixture_directory() as folder:
            args=['program','--original','missing.xlsx','--triage','missing.json','--returned','missing.xlsx','--output-dir',str(folder)]
            with patch('sys.argv',args),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit): importer.main()


if __name__=='__main__':
    unittest.main()

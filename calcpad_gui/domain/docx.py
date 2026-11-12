"""DocxProcessing implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from pathlib import Path
import shutil

class DocxProcessing:
    """GTK-independent behavior; callable names retained for compatibility."""

    @staticmethod
    def _process_ooxml_formula_runs(data, use_comma):
        """Preserve OMML; set decimal separator and color unit formula runs green."""
        import re as _re
        run_re = _re.compile(rb"<m:r(?:\s[^>]*)?>.*?</m:r>", _re.DOTALL)
        text_re = _re.compile(rb"<m:t(?:\s[^>]*)?>(.*?)</m:t>", _re.DOTALL)
        decimal_re = _re.compile(rb"(?<=\d)[.,](?=\d)")
        decimal = b"," if use_comma else b"."
        unit_re = _re.compile(
            rb"(?:mm|cm|km|m|ms|s|min|h|mV|kV|V|uV|\xc2\xb5V|\xce\xbcV|"
            rb"mA|A|uA|\xc2\xb5A|\xce\xbcA|mW|kW|W|"
            rb"mF|nF|pF|F|uF|\xc2\xb5F|\xce\xbcF|"
            rb"mH|nH|H|uH|\xc2\xb5H|\xce\xbcH|"
            rb"Hz|kHz|MHz|Pa|kPa|MPa|\xce\xa9|k\xce\xa9|M\xce\xa9|%|\xc2\xb0C|K)"
        )
        def process_run(match):
            run=match.group(0)
            tm=text_re.search(run)
            if not tm:
                return run
            old_text=tm.group(1)
            new_text=decimal_re.sub(decimal,old_text)
            if new_text != old_text:
                run=run[:tm.start(1)]+new_text+run[tm.end(1):]
            if not unit_re.fullmatch(new_text.strip()):
                return run
            color=b'<w:color w:val="119911" />'
            wrpr=_re.search(rb"<w:rPr>(.*?)</w:rPr>",run,_re.DOTALL)
            if wrpr:
                content=wrpr.group(1)
                if b'<w:color ' in content:
                    content=_re.sub(rb'<w:color\s+[^>]*/>',color,content,count=1)
                else:
                    content=color+content
                return run[:wrpr.start(1)]+content+run[wrpr.end(1):]
            mt_pos=run.find(b'<m:t')
            if mt_pos >= 0:
                return run[:mt_pos]+b'<w:rPr>'+color+b'</w:rPr>'+run[mt_pos:]
            return run
        return run_re.sub(process_run,data)

    def _postprocess_docx(self, docx_path, use_comma):
        import zipfile
        tmp=docx_path+'.tmp'
        try:
            with zipfile.ZipFile(docx_path,'r') as zin:
                with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as zout:
                    for item in zin.infolist():
                        data=zin.read(item.filename)
                        if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                            data=self._process_ooxml_formula_runs(data,use_comma)
                        zout.writestr(item,data)
            shutil.move(tmp,docx_path)
        finally:
            try: Path(tmp).unlink(missing_ok=True)
            except OSError: pass

    def _apply_decimal_comma_docx(self, docx_path):
        self._postprocess_docx(docx_path,True)

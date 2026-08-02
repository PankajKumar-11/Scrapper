import os
import re
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try importing Jinja2
try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

class LaTeXRenderer:
    def __init__(self, template_path: str = "templates/resume_template.tex", compiler: str = "pdflatex"):
        self.template_path = template_path
        self.compiler = compiler

    def escape_latex(self, text: str) -> str:
        """Escapes LaTeX special characters to prevent compilation errors."""
        if not isinstance(text, str):
            return text
        
        # Don't double escape URLs
        if text.startswith("http://") or text.startswith("https://"):
            return text

        chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}'
        }
        regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(chars.keys(), key=lambda item: -len(item))))
        return regex.sub(lambda match: chars[match.group()], text)

    def _sanitize_dict(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._sanitize_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_dict(item) for item in obj]
        elif isinstance(obj, str):
            return self.escape_latex(obj)
        return obj

    def render_tex(self, resume_data: Dict[str, Any]) -> str:
        sanitized_data = self._sanitize_dict(resume_data)

        if not HAS_JINJA2:
            raise RuntimeError("Jinja2 package is not installed. Please run `pip install jinja2`.")

        template_file = Path(self.template_path)
        if not template_file.exists():
            raise FileNotFoundError(f"LaTeX template not found at {self.template_path}")

        env = jinja2.Environment(
            block_start_string='((*',
            block_end_string='*))',
            variable_start_string='((',
            variable_end_string='))',
            loader=jinja2.FileSystemLoader(template_file.parent)
        )
        template = env.get_template(template_file.name)
        return template.render(**sanitized_data)

    def compile_pdf(self, resume_data: Dict[str, Any], output_dir: Path, file_prefix: str) -> Optional[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        tex_content = self.render_tex(resume_data)

        tex_path = output_dir / f"{file_prefix}.tex"
        pdf_path = output_dir / f"{file_prefix}.pdf"

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        logger.info(f"Generated LaTeX source file: {tex_path}")

        # Check if pdflatex or xelatex executable is present
        try:
            cmd = [self.compiler, "-interaction=nonstopmode", f"-output-directory={output_dir.resolve()}", str(tex_path.resolve())]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            
            if res.returncode == 0 and pdf_path.exists():
                logger.info(f"Successfully compiled PDF: {pdf_path}")
                return pdf_path
            else:
                logger.warning(f"LaTeX compilation exited with code {res.returncode}. Source .tex saved at {tex_path}")
                return None
        except FileNotFoundError:
            logger.warning(f"LaTeX compiler '{self.compiler}' not found in system PATH. Rendered .tex file is available at {tex_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to compile PDF for {file_prefix}: {e}")
            return None

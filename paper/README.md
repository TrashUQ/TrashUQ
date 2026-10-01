# Paper deliverables

`main.pdf` is the presentation/submission PDF. `main.tex`, `sections/`, and
`references.bib` are its sources. The local IOS class, bibliography styles, and
support packages are retained for reproducible builds.

Compile from this directory with a TeX distribution containing the required packages:

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Review the resulting PDF before replacing a submitted version. The root
`trashuq-paper.zip`, when present, is an ignored export and may be older than the sources.

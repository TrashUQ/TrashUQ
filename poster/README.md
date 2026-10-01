# Conference poster

- `main.pdf`: final A1 portrait poster for printing.
- `main.tex`: poster source, including vector diagrams and the website QR code.
- `preview.png`: convenient preview for review and sharing.

Compile from this directory:

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Review at full size and scan the QR code before printing. Its destination is
`https://trashuq.vercel.app`; landing-page source is in `../poster-web/`.

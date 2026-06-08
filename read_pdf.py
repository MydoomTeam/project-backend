try:
    import pypdf
    with open('Proyecto - Entrega_05 - Módulo de testing V2.pdf', 'rb') as f:
        pdf = pypdf.PdfReader(f)
        for i, page in enumerate(pdf.pages):
            print(f"--- PAGE {i+1} ---")
            print(page.extract_text())
except ImportError:
    print("pypdf not installed")
except Exception as e:
    print(f"Error: {e}")

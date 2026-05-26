import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      return NextResponse.json({ success: false, error: 'No file provided in payload.' }, { status: 400 });
    }

    // Forward the FormData stream directly to our new FastAPI microservice
    const backendFormData = new FormData();
    backendFormData.append('file', file);

    const backendRes = await fetch('http://localhost:8000/claims/upload', {
      method: 'POST',
      body: backendFormData,
    });

    if (!backendRes.ok) {
        let errSnippet = "Unknown Backend Error";
        try {
            const errObj = await backendRes.json();
            errSnippet = errObj.detail || errObj.error || errSnippet;
        } catch {
            errSnippet = await backendRes.text();
        }
        return NextResponse.json({ success: false, error: errSnippet }, { status: 500 });
    }

    const parsed = await backendRes.json();

    return NextResponse.json({
       success: true,
       audit_run: parsed
    });
    
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}

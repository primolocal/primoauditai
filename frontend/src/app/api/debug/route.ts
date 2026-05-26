import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';

const execAsync = promisify(exec);

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get('file') as File;
    if (!file) {
      return NextResponse.json({ error: 'No file provided in payload.' }, { status: 400 });
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const tempDir = path.join(process.cwd(), '.next', 'cache', 'uploads');
    if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
    
    const tempPath = path.join(tempDir, `debug_${Date.now()}.zip`);
    fs.writeFileSync(tempPath, buffer);

    const pythonExecutable = path.join(process.cwd(), 'backend', 'venv', 'Scripts', 'python.exe');
    const parserScript = path.join(process.cwd(), 'backend', 'main.py');
    const pythonCommand = fs.existsSync(pythonExecutable) ? `"${pythonExecutable}"` : 'python';
    
    const { stdout, stderr } = await execAsync(`${pythonCommand} "${parserScript}" "${tempPath}"`);
    try { fs.unlinkSync(tempPath); } catch (e) {}
    
    if (stderr && !stdout) {
       console.error("Python Stderr:", stderr);
       return NextResponse.json({ error: "Parser module encountered a fatal Python error.", stderr }, { status: 500 });
    }

    const parsed = JSON.parse(stdout);
    if (parsed.error) {
       return NextResponse.json({ error: parsed.error }, { status: 500 });
    }

    // Bypass any and all UI mappings and strictly return natively parsed data 
    return NextResponse.json(parsed);
    
  } catch (error: any) {
    console.error("Debug Upload Error:", error);
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}

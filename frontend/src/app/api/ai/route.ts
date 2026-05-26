import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { action, issueId, facts, conclusion } = await request.json();

    // Simulate AI processing
    await new Promise((resolve) => setTimeout(resolve, 1500));

    if (action === 'explain') {
      return NextResponse.json({
        explanation: `Based on the facts provided: ${facts.join(', ')}. The system concluded that ${conclusion}. As an AI assistant, I recommend reviewing the visual evidence to ensure there is no hidden damage before making a final decision.`
      });
    }

    if (action === 'generateNote') {
      return NextResponse.json({
        note: `[Audit Note - System Generated]\nIssue ID: ${issueId}\nFindings: ${conclusion}\nFacts: ${facts.join('; ')}\nAction required by appraiser: Provide additional visual documentation or revise estimate.`
      });
    }

    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
  } catch (error) {
    console.error('Error in mock AI endpoint:', error);
    return NextResponse.json({ error: 'Failed to generate AI response' }, { status: 500 });
  }
}

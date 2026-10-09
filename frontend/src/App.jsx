import React, { useState } from 'react';
import Navbar from './components/Navbar';
import ChatPanel from './components/ChatPanel';
import TracePanel from './components/TracePanel';
import GraphView from './components/GraphView';
import Dashboard from './components/Dashboard';
import AblationModal from './components/AblationModal';
import { streamChat } from './lib/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('demo'); // 'demo' | 'dashboard'
  const [isProcessing, setIsProcessing] = useState(false);
  const [traceEvents, setTraceEvents] = useState([]);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [activeCaseData, setActiveCaseData] = useState(null);
  const [isAblationOpen, setIsAblationOpen] = useState(false);

  const handleSendMessage = async ({ customerId, message }) => {
    setIsProcessing(true);
    setTraceEvents([]);
    setCurrentResponse(null);
    setActiveCaseData(null);

    // Append customer message immediately to history
    const historyIndex = chatHistory.length;
    setChatHistory(prev => [
      ...prev,
      { customerId, customerMessage: message, response: null }
    ]);

    await streamChat(
      { customerId, message },
      {
        onTrace: (event) => {
          setTraceEvents(prev => [...prev, event]);
          if (event.data?.autonomy_level) {
            setActiveCaseData(prev => ({
              ...prev,
              autonomy_level: event.data.autonomy_level,
              confidence: event.data.confidence || event.data.resolution_confidence || prev?.confidence,
            }));
          }
        },
        onResponse: (response) => {
          setCurrentResponse(response);
          setActiveCaseData(response);
          // Update last chat history item with response
          setChatHistory(prev => {
            const next = [...prev];
            if (next[historyIndex]) {
              next[historyIndex].response = response;
            }
            return next;
          });
        },
        onDone: () => {
          setIsProcessing(false);
        },
        onError: (err) => {
          console.error('SSE Error:', err);
          setIsProcessing(false);
          const errorResponse = {
            response_text: `System Alert: ${err.message || 'Error communicating with agent.'}`,
            autonomy_level: 'blocked',
          };
          setCurrentResponse(errorResponse);
          setChatHistory(prev => {
            const next = [...prev];
            if (next[historyIndex]) {
              next[historyIndex].response = errorResponse;
            }
            return next;
          });
        },
      }
    );
  };

  const handleReset = () => {
    setTraceEvents([]);
    setCurrentResponse(null);
    setChatHistory([]);
    setActiveCaseData(null);
    setIsProcessing(false);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#09090b] text-zinc-100 selection:bg-emerald-500/20 selection:text-emerald-300">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAblation={() => setIsAblationOpen(true)}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'demo' ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* 2-Panel Core: Left Chat, Right Trace */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
              <div className="lg:col-span-5 h-[calc(100vh-16rem)] lg:h-[calc(100vh-13rem)] overflow-hidden">
                <ChatPanel
                  onSendMessage={handleSendMessage}
                  isProcessing={isProcessing}
                  currentResponse={currentResponse}
                  chatHistory={chatHistory}
                  onReset={handleReset}
                />
              </div>

              <div className="lg:col-span-7 h-[calc(100vh-16rem)] lg:h-[calc(100vh-13rem)] overflow-hidden">
                <TracePanel
                  traceEvents={traceEvents}
                  isProcessing={isProcessing}
                  activeCaseData={activeCaseData}
                />
              </div>
            </div>

            {/* Bottom LangGraph Visualizer */}
            <GraphView
              traceEvents={traceEvents}
              activeCaseData={activeCaseData}
            />
          </div>
        ) : (
          <Dashboard />
        )}
      </main>

      {/* Ablation Study Modal */}
      <AblationModal
        isOpen={isAblationOpen}
        onClose={() => setIsAblationOpen(false)}
      />
    </div>
  );
}

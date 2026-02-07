import { useRef, useEffect, useCallback, useState } from 'react';
import { Hand, Github, BookOpen } from 'lucide-react';
import { Camera } from './components/Camera';
import type { CameraRef } from './components/Camera';
import { TranslationPanel } from './components/TranslationPanel';
import { Controls } from './components/Controls';
import { StatusBar } from './components/StatusBar';
import { useWebSocket } from './hooks/useWebSocket';
import { useAppStore } from './store/useAppStore';
import { translateSigns, clearSession as clearSessionApi } from './services/api';
import './App.css';

function App() {
  const cameraRef = useRef<CameraRef>(null);
  const frameIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const accumulatedSignsRef = useRef<string[]>([]);
  
  const [lastSign, setLastSign] = useState<string | null>(null);
  const [lastConfidence, setLastConfidence] = useState(0);

  const {
    isConnected,
    connect,
    disconnect,
    sendFrame,
    lastMessage,
    sendCommand,
  } = useWebSocket();

  const {
    isTranslating,
    sessionId,
    detectedSigns,
    startTranslation,
    stopTranslation,
    addDetectedSign,
    setCurrentSentence,
    clearSession: clearStore,
    addToHistory,
  } = useAppStore();

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'detection') {
      const { sign, confidence } = lastMessage.payload;
      
      if (sign) {
        setLastSign(sign);
        setLastConfidence(confidence || 0);
        
        // Only add unique consecutive signs
        const lastAdded = accumulatedSignsRef.current[accumulatedSignsRef.current.length - 1];
        if (sign !== lastAdded) {
          accumulatedSignsRef.current.push(sign);
          addDetectedSign(sign);
        }
      }
    }
  }, [lastMessage, addDetectedSign]);

  // Start translation - connect WebSocket and start sending frames
  const handleStart = useCallback(() => {
    startTranslation();
    connect();

    // Start frame capture loop
    if (cameraRef.current) {
      frameIntervalRef.current = setInterval(() => {
        const frame = cameraRef.current?.captureFrame();
        if (frame && isConnected) {
          sendFrame(frame);
        }
      }, 1000 / 10); // 10 FPS
    }
  }, [startTranslation, connect, sendFrame, isConnected]);

  // Stop translation
  const handleStop = useCallback(() => {
    stopTranslation();
    disconnect();

    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  }, [stopTranslation, disconnect]);

  // Clear session
  const handleClear = useCallback(async () => {
    // Clear in backend
    try {
      await clearSessionApi(sessionId);
    } catch (e) {
      console.log('Session clear failed or not needed');
    }

    // Send clear command via WebSocket
    sendCommand('clear');

    // Clear local state
    clearStore();
    accumulatedSignsRef.current = [];
    setLastSign(null);
    setLastConfidence(0);
  }, [sessionId, sendCommand, clearStore]);

  // Process accumulated signs into sentence when user stops
  const handleProcessTranslation = useCallback(async () => {
    const signs = accumulatedSignsRef.current;
    if (signs.length === 0) return;

    try {
      const result = await translateSigns(signs, sessionId);
      setCurrentSentence(result.translation);
      
      // Add to history
      addToHistory({
        signs: [...signs],
        translation: result.translation,
        timestamp: Date.now(),
      });

      // Clear accumulated signs for next sentence
      accumulatedSignsRef.current = [];
    } catch (error) {
      console.error('Translation failed:', error);
    }
  }, [sessionId, setCurrentSentence, addToHistory]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
      disconnect();
    };
  }, [disconnect]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Hand className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  AI Sign Language Translator
                </h1>
                <p className="text-sm text-gray-500">
                  Real-time sign language to text translation
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/rakhatdiploma/iitudiplomas"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <Github className="w-5 h-5" />
                <span className="hidden sm:inline">GitHub</span>
              </a>
              <a
                href="/docs"
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <BookOpen className="w-5 h-5" />
                <span className="hidden sm:inline">Docs</span>
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Bar */}
        <div className="mb-6">
          <StatusBar />
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Camera Section */}
          <div className="space-y-4">
            <Camera
              ref={cameraRef}
              isTranslating={isTranslating}
            />
            
            {/* Manual Process Button */}
            {detectedSigns.length > 0 && (
              <button
                onClick={handleProcessTranslation}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors shadow-md"
              >
                Process Signs into Sentence
              </button>
            )}
          </div>

          {/* Translation Panel */}
          <TranslationPanel
            lastSign={lastSign}
            confidence={lastConfidence}
          />
        </div>

        {/* Controls */}
        <Controls
          onStart={handleStart}
          onStop={handleStop}
          onClear={handleClear}
        />

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            How to Use
          </h3>
          <ol className="space-y-2 text-blue-800">
            <li className="flex items-start gap-2">
              <span className="font-bold">1.</span>
              <span>Allow camera access when prompted</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">2.</span>
              <span>Click "Start Translation" to begin</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">3.</span>
              <span>Make ASL signs in front of the camera (A-Z, 0-9 supported)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">4.</span>
              <span>Click "Process Signs into Sentence" to translate your signs</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">5.</span>
              <span>Click "Clear" to start a new session</span>
            </li>
          </ol>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500">
            <p>
              IITU Diploma Project • Team: Ulzhan, Vlad, Rakhat
            </p>
            <p>
              Session ID: <span className="font-mono">{sessionId}</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

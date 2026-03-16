"use client";

import { useState, useRef } from "react";

// --- NEW COMPONENT: UploadArea ---
function UploadArea() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("Select a file to upload (e.g., timetable.csv, inventory.xlsx, syllabus.pdf, lab-manual.docx)");
  const [isUploading, setIsUploading] = useState(false);
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setMessage(`Selected file: ${e.target.files[0].name}`);
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select a file first.");
      return;
    }
    setIsUploading(true);
    setMessage(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/api/upload/file`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setMessage(`Success! ${data.message}`);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsUploading(false);
      setFile(null);
    }
  };

  return (
    <div className="upload-area">
      <h2>Upload Data</h2>
      <p>{message}</p>
      <input 
        type="file" 
        onChange={handleFileChange} 
        disabled={isUploading} 
        accept=".pdf,.docx,.csv,.xlsx"
      />
      <button 
        className="upload-btn" 
        onClick={handleUpload} 
        disabled={isUploading || !file}
      >
        {isUploading ? "Uploading..." : "Upload"}
      </button>
      <style jsx>{`
        .upload-area {
          padding: 2rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          align-items: center;
          justify-content: center;
          height: 100%;
        }
        .upload-btn {
          padding: 0.5rem 1rem;
          background-color: #007bff;
          color: white;
          border: none;
          border-radius: 5px;
          cursor: pointer;
        }
        .upload-btn:disabled {
          background-color: #aaa;
        }
      `}</style>
    </div>
  );
}
// --- END NEW COMPONENT ---


export default function Page() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [module, setModule] = useState("AUTO");
  const chatRef = useRef(null);

  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const endpointMap = {
    "AUTO": "/api/query/eeeva",
    "SYLLABUS": "/api/query/syllabus",
    "LAB MANUALS": "/api/query/labmanual",
    "TIMETABLE": "/api/query/timetable",
    "INVENTORY": "/api/query/inventory",
  };
  
  const moduleButtons = [
    "SYLLABUS",
    "LAB MANUALS",
    "TIMETABLE",
    "INVENTORY",
    "UPLOAD DATA",
  ];

  const scrollToBottom = () => {
    setTimeout(() => {
      if (chatRef.current) {
        chatRef.current.scrollTop = chatRef.current.scrollHeight;
      }
    }, 50);
  };

  const sendMessage = async () => {
    const question = input.trim();
    if (!question) return;

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    scrollToBottom();
    
    const endpointKey = endpointMap[module] ? module : "AUTO";
    const endpoint = endpointMap[endpointKey];

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      
      if (!response.ok) {
        const errData = await response.json();
        const errorText = errData.detail || `An error occurred (Status: ${response.status})`;
        setMessages((prev) => [...prev, { role: "bot", text: errorText }]);
        scrollToBottom();
        return;
      }
      const data = await response.json();
      const botText = data.answer || "I found relevant information, but couldn't form an answer.";
      setMessages((prev) => [...prev, { role: "bot", text: botText }]);
      scrollToBottom();
    } catch (error) {
      console.error("Fetch error:", error);
      setMessages((prev) => [...prev, { role: "bot", text: "Failed to connect to the backend." }]);
      scrollToBottom();
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleModuleClick = (m) => {
    setModule(prev => prev === m ? "AUTO" : m);
  };

  // --- THIS IS YOUR FULL, CORRECTED UI ---
  return (
    <div className="container">
      {/* HEADER (RESTORED) */}
      <div className="header">
        <h1>EEEVA</h1>
        <div className="header-center">How Can I Help?</div>
        <button className="id-button">ID</button>
      </div>

      {/* CONTENT */}
      <div className="content">
        {/* LEFT HISTORY PANEL (RESTORED) */}
        <div className="sidebar">
          <div className="history">History</div>
          <div className="history-list">
            {messages.map((m, idx) => (
              <div className="history-item" key={idx}>
                {m.role === "user" ? "You: " : "EEEVA: "}
                {m.text && m.text.slice(0, 25)}...
              </div>
            ))}
          </div>
        </div>

        {/* DYNAMIC CHAT AREA (YOUR NEW FUNCTIONALITY) */}
        <div className="chat-area">
          {module === "UPLOAD DATA" ? (
            <UploadArea />
          ) : (
            <>
              {/* This is your original chat UI */}
              <div className="messages" ref={chatRef}>
                {messages.map((m, idx) => (
                  <div className={`message ${m.role}`} key={idx}>
                    <b>{m.role === "user" ? "You" : "EEEVA"}</b>
                    <p>{m.text}</p>
                  </div>
                ))}
              </div>

              <div className="input-area">
                <div className="input-box">
                  <textarea
                    placeholder="Ask something..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKey}
                  />
                  <button className="send-button" onClick={sendMessage}>
                    ➤
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* RIGHT MODULE BUTTONS (YOUR NEW FUNCTIONALITY) */}
        <div className="modules-container">
          {moduleButtons.map(
            (m) => (
              <button
                key={m}
                className={`module-btn ${module === m ? "active" : ""}`}
                onClick={() => handleModuleClick(m)}
              >
                {m}
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
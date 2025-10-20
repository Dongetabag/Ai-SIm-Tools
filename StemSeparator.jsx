import React, { useState, useCallback } from 'react';
import { Upload, Music, Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

const StemSeparator = () => {
  const [file, setFile] = useState(null);
  const [model, setModel] = useState('htdemucs');
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const models = [
    { value: 'htdemucs', label: 'HTDemucs (Recommended)', description: 'Fast, good quality' },
    { value: 'htdemucs_ft', label: 'HTDemucs Fine-tuned', description: 'Fine-tuned version' },
    { value: 'mdx_extra', label: 'MDX Extra', description: 'Best quality (slower)' },
    { value: 'mdx_extra_q', label: 'MDX Extra Q', description: 'Fast processing' }
  ];

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type.startsWith('audio/') || 
          droppedFile.name.endsWith('.mp3') || 
          droppedFile.name.endsWith('.wav') || 
          droppedFile.name.endsWith('.flac')) {
        setFile(droppedFile);
      } else {
        alert('Please upload an audio file (MP3, WAV, FLAC)');
      }
    }
  }, []);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const uploadAndSeparate = async () => {
    if (!file) {
      alert('Please select an audio file first');
      return;
    }

    setIsUploading(true);
    setStatus({ type: 'uploading', message: 'Uploading file...' });

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', model);

      const response = await fetch('/api/separate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setJobId(result.job_id);
      setStatus({ type: 'processing', message: 'Processing audio...' });
      
      // Start polling for status
      pollStatus(result.job_id);
      
    } catch (error) {
      console.error('Upload error:', error);
      setStatus({ type: 'error', message: `Upload failed: ${error.message}` });
    } finally {
      setIsUploading(false);
    }
  };

  const pollStatus = async (jobId) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/status/${jobId}`);
        const data = await response.json();
        
        if (data.status === 'completed') {
          setStatus({ type: 'completed', message: 'Separation completed!', stems: data.stems });
        } else if (data.status === 'failed') {
          setStatus({ type: 'error', message: `Processing failed: ${data.error}` });
        } else if (data.status === 'processing') {
          setStatus({ type: 'processing', message: 'Processing audio...' });
          setTimeout(poll, 2000); // Poll every 2 seconds
        }
      } catch (error) {
        console.error('Status check error:', error);
        setStatus({ type: 'error', message: 'Failed to check status' });
      }
    };
    
    poll();
  };

  const downloadStem = async (stemName) => {
    if (!jobId) return;
    
    try {
      const response = await fetch(`/api/download/${jobId}/${stemName}`);
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${file?.name.replace(/\.[^/.]+$/, '')}_${stemName}.wav`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
      alert('Download failed');
    }
  };

  const reset = () => {
    setFile(null);
    setJobId(null);
    setStatus(null);
    setModel('htdemucs');
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <div className="text-center mb-8">
        <Music className="w-16 h-16 mx-auto mb-4 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Stem Separator</h1>
        <p className="text-gray-600">Separate vocals, drums, bass, and other instruments using AI</p>
      </div>

      {!status && (
        <div className="space-y-6">
          {/* File Upload */}
          <div
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive 
                ? 'border-blue-500 bg-blue-50' 
                : file 
                  ? 'border-green-500 bg-green-50' 
                  : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept="audio/*,.mp3,.wav,.flac"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            
            {file ? (
              <div className="space-y-2">
                <CheckCircle className="w-12 h-12 mx-auto text-green-500" />
                <p className="text-lg font-medium text-green-700">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <button
                  onClick={() => setFile(null)}
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Remove file
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="w-12 h-12 mx-auto text-gray-400" />
                <p className="text-lg font-medium text-gray-700">
                  Drop your audio file here or click to browse
                </p>
                <p className="text-sm text-gray-500">
                  Supports MP3, WAV, FLAC (max 100MB)
                </p>
              </div>
            )}
          </div>

          {/* Model Selection */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Choose AI Model
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {models.map((modelOption) => (
                <label
                  key={modelOption.value}
                  className={`relative flex items-start p-4 border rounded-lg cursor-pointer transition-colors ${
                    model === modelOption.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="model"
                    value={modelOption.value}
                    checked={model === modelOption.value}
                    onChange={(e) => setModel(e.target.value)}
                    className="sr-only"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">
                      {modelOption.label}
                    </div>
                    <div className="text-sm text-gray-500">
                      {modelOption.description}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Upload Button */}
          <button
            onClick={uploadAndSeparate}
            disabled={!file || isUploading}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Uploading...</span>
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                <span>Start Separation</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Status Display */}
      {status && (
        <div className="space-y-6">
          <div className={`p-4 rounded-lg ${
            status.type === 'error' 
              ? 'bg-red-50 border border-red-200' 
              : status.type === 'completed'
                ? 'bg-green-50 border border-green-200'
                : 'bg-blue-50 border border-blue-200'
          }`}>
            <div className="flex items-center space-x-3">
              {status.type === 'error' ? (
                <AlertCircle className="w-6 h-6 text-red-500" />
              ) : status.type === 'completed' ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
              )}
              <div>
                <p className={`font-medium ${
                  status.type === 'error' 
                    ? 'text-red-700' 
                    : status.type === 'completed'
                      ? 'text-green-700'
                      : 'text-blue-700'
                }`}>
                  {status.message}
                </p>
                {status.type === 'processing' && (
                  <p className="text-sm text-blue-600 mt-1">
                    This may take a few minutes...
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Download Stems */}
          {status.type === 'completed' && status.stems && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Download Separated Stems
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(status.stems).map(([stemName, stemInfo]) => (
                  <div
                    key={stemName}
                    className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900 capitalize">
                        {stemName}
                      </h4>
                      <span className="text-xs text-gray-500">
                        {(stemInfo.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>
                    <button
                      onClick={() => downloadStem(stemName)}
                      className="w-full bg-blue-600 text-white py-2 px-3 rounded text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reset Button */}
          <div className="text-center">
            <button
              onClick={reset}
              className="bg-gray-600 text-white py-2 px-6 rounded-lg font-medium hover:bg-gray-700 transition-colors"
            >
              Process Another File
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StemSeparator;

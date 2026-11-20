import { useState, useEffect } from 'react'
import './CodeBlock.css'

function CodeBlock({ language = 'text', code }) {
  const [copied, setCopied] = useState(false)

  const detectLanguage = (lang) => {
    if (!lang) return 'text'
    const langs = {
      js: 'javascript', javascript: 'javascript',
      ts: 'typescript', typescript: 'typescript',
      py: 'python', python: 'python',
      java: 'java',
      cpp: 'cpp', cxx: 'cpp', cc: 'cpp',
      c: 'c',
      cs: 'csharp', csharp: 'csharp',
      go: 'go', golang: 'go',
      rs: 'rust', rust: 'rust',
      rb: 'ruby', ruby: 'ruby',
      php: 'php',
      swift: 'swift',
      kt: 'kotlin', kotlin: 'kotlin',
      sh: 'bash', bash: 'bash',
      sql: 'sql',
      html: 'html',
      css: 'css',
      json: 'json',
      yaml: 'yaml', yml: 'yaml',
      xml: 'xml',
      md: 'markdown', markdown: 'markdown',
    }
    return langs[lang.toLowerCase()] || 'text'
  }

  const langClass = detectLanguage(language)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Copy failed:', err)
    }
  }

  const formatCode = (code) => {
    if (!code) return ''
    
    // Simple syntax highlighting (for demonstration)
    const keywords = ['def', 'class', 'return', 'if', 'else', 'for', 'while', 'import', 'from', 'const', 'let', 'var', 'function', 'async', 'await', 'try', 'catch', 'throw']
    
    return code.replace(/(".*?"|'.*?')/g, '<span class="string">$1</span>')
               .replace(/\b(\d+\.?\d*)\b/g, '<span class="number">$1</span>')
               .replace(new RegExp(`\\b(${keywords.join('|')})\\b`, 'g'), '<span class="keyword">$1</span>')
               .replace(/(\/\/.*|\#.*)/g, '<span class="comment">$1</span>')
               .replace(/\/\*[\s\S]*?\*\//g, '<span class="comment">$&</span>')
               .replace(/\.(\w+)/g, '.<span class="method">$1</span>')
  }

  return (
    <div className="code-block">
      <div className="code-header">
        <span className="code-lang">{langClass.toUpperCase()}</span>
        <button onClick={handleCopy} className="copy-btn">
          {copied ? (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 6L9 17l-5-5"/>
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
              </svg>
              Copy code
            </>
          )}
        </button>
      </div>
      <div className="code-content">
        <pre>
          <code 
            className={`language-${langClass}`}
            dangerouslySetInnerHTML={{ __html: formatCode(code) }}
          />
        </pre>
      </div>
    </div>
  )
}

export default CodeBlock

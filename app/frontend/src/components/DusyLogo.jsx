import React from 'react';

export function DusyLogoIcon({ size = 24, className = "" }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Subtle medical cross backdrop */}
      <rect x="9.5" y="3.5" width="5" height="17" rx="2" fill="white" fillOpacity="0.25" />
      <rect x="3.5" y="9.5" width="17" height="5" rx="2" fill="white" fillOpacity="0.25" />
      {/* Crisp clinical ECG heartbeat telemetry */}
      <path 
        d="M2.5 12h4l2.2-5.5 4.6 11 2.5-6.5H21.5" 
        stroke="white" 
        strokeWidth="2.5" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
      />
    </svg>
  );
}

export default function DusyLogo({ showText = true, className = "" }) {
  return (
    <div className={`dusy-brand-wrap ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '12px' }}>
      <div className="logo-badge">
        <DusyLogoIcon size={24} />
      </div>
      {showText && <span className="logo-text">DUSY</span>}
    </div>
  );
}

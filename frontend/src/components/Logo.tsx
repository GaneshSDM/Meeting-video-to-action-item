import React from "react";

const Logo: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <img
      src="/assets/decision-minds-logo.png"
      alt="Decision Minds"
      className="h-11 w-auto object-contain"
    />
  </div>
);

export default Logo;

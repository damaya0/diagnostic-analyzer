// ErrorContext.js
import React, { createContext, useContext, useState } from "react";
const GlobalContext = createContext();

export function useError() {
  return useContext(GlobalContext);
}

export function GlobalContextProvider({ children }) {
  const [analysisData, setAnalysisData] = useState("NJKHCJHDCUI");
  const [results, setResults] = useState(null);
  return (
    <GlobalContext.Provider value={{ analysisData, setAnalysisData, results, setResults }}>
      {children}
    </GlobalContext.Provider>
  );
}

export default GlobalContext;

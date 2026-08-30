import React, { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [role, setRole] = useState(() => {
    return localStorage.getItem("eventpath_user_role") || "ADMIN";
  });

  useEffect(() => {
    localStorage.setItem("eventpath_user_role", role);
  }, [role]);

  const toggleRole = () => {
    setRole((prev) => (prev === "ADMIN" ? "USER" : "ADMIN"));
  };

  const isAdmin = role === "ADMIN";

  return (
    <AuthContext.Provider value={{ role, setRole, toggleRole, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

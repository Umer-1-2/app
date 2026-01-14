import { useState } from "react";

function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = async () => {
    const res = await fetch("http://127.0.0.1:8000/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role);
      alert(`Logged in as ${data.role}`);
    } else {
      alert(data.detail);
    }
  };

  return (
    <div style={{ padding: 40 }}>
      <h2>WorkShift Login</h2>

      <input
        placeholder="Email"
        value={email}
        onChange={e => setEmail(e.target.value)}
      /><br /><br />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
      /><br /><br />

      <button onClick={login}>Login</button>
    </div>
  );
}

export default App;

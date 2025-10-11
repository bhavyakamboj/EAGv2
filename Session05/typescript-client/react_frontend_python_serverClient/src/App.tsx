import { useState } from 'react'
import './App.css'

function App() {
    const [text, setText] = useState('')
    const [reversed, setReversed] = useState('')
    const [loading, setLoading] = useState(false)

    const handleReverse = async () => {
        setLoading(true)
        try {
            const response = await fetch('http://localhost:8080', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            })
            const data = await response.json()
            setReversed(data.reversed)
        } catch (error) {
            console.error('Error:', error)
            alert('Failed to reverse text. Make sure the server is running.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container">
            <h1>String Reverser</h1>
            <div className="input-group">
                <input
                    type="text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Enter text to reverse"
                    className="text-input"
                />
                <button
                    onClick={handleReverse}
                    disabled={loading || !text}
                    className="reverse-button"
                >
                    {loading ? 'Reversing...' : 'Reverse'}
                </button>
            </div>
            {reversed && (
                <div className="result">
                    <h2>Result:</h2>
                    <p>{reversed}</p>
                </div>
            )}
        </div>
    )
}

export default App 
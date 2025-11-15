import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';

function App() {
  const [words, setWords] = React.useState([]);
  const [userWord, setUserWord] = React.useState('');
  const [results, setResults] = React.useState([]);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    fetch('http://localhost:8000/words')
      .then(res => res.json())
      .then(data => setWords(data.words))
      .catch(error => console.error('Error fetching words:', error));
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!userWord.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_word: userWord }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Error searching:', error);
      alert('Error searching for similar words: ' + error.message);
    }
    setLoading(false);
  };

  return React.createElement('div', { className: 'app' },
    React.createElement('h1', null, 'Jane\'s Similar Word Search'),
    
    React.createElement('div', { className: 'words-section' },
      React.createElement('h3', null, 'Available Words:'),
      React.createElement('div', { className: 'words-list' },
        words.map((word, index) =>
          React.createElement('span', { 
            key: index, 
            className: 'word',
            onClick: () => setUserWord(word)
          }, word)
        )
      )
    ),

    React.createElement('div', { className: 'search-section' },
      React.createElement('h2', { className: 'search-title' }, 'Find Similar Words'),
      
      React.createElement('form', { className: 'search-form', onSubmit: handleSearch },
        React.createElement('div', { className: 'search-input-container' },
          React.createElement('input', {
            type: 'text',
            className: 'search-input',
            value: userWord,
            onChange: (e) => setUserWord(e.target.value),
            placeholder: 'Type a word to find similarities...'
          }),
          React.createElement('span', { className: 'search-input-icon' }, '✨')
        ),
        React.createElement('button', { 
          type: 'submit', 
          className: 'search-button',
          disabled: loading 
        },
          loading ? 
            React.createElement(React.Fragment, null,
              React.createElement('span', { className: 'button-icon' }, '⏳'),
              ' Searching...'
            ) :
            React.createElement(React.Fragment, null,
              React.createElement('span', { className: 'button-icon' }, '🚀'),
              ' Find Similar'
            )
        )
      )
    ),

    results.length > 0 && React.createElement('div', { className: 'results' },
      React.createElement('h3', null, 'Similar Words Found:'),
      React.createElement('div', { className: 'results-grid' },
        results.map((result, index) =>
          React.createElement('div', { key: index, className: 'result' },
            React.createElement('div', { className: 'result-header' },
              React.createElement('strong', null, result.word),
              React.createElement('span', { className: 'score' }, `Score: ${result.score}`)
            ),
            React.createElement('p', null, result.reason)
          )
        )
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  React.createElement(React.StrictMode, null,
    React.createElement(App)
  )
);
import { useState, useEffect } from 'react'

function App() {
  const [schedule, setSchedule] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/data/schedule.json')
      .then(r => r.json())
      .then(data => {
        setSchedule(data)
        setLoading(false)
      })
      .catch(err => {
        console.warn('⚠️ schedule.json not found. Using mock data.')
        setLoading(false)
        setSchedule([
          {
            channel: "CTC",
            program: "Новости",
            is_live: true,
            start: "20:00",
            end: "20:30",
            stream_url: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
            logo: "https://upload.wikimedia.org/wikipedia/commons/c/c3/CTC_logo_2015.png"
          }
        ])
      })
  }, [])

  if (loading) return <div className="flex justify-center items-center h-screen">⏳ Loading…</div>

  return (
    <div className="min-h-screen bg-black text-white font-sans">
      <header className="text-center py-6">
        <h1 className="text-3xl md:text-4xl font-black tracking-tight bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
          🔥 live-programm
        </h1>
        <p className="text-gray-400 mt-2">Только то, что сейчас в эфире</p>
      </header>

      <div className="space-y-3 p-4 max-w-3xl mx-auto">
        {schedule.map((item, i) => (
          <ScheduleCard key={i} item={item} />
        ))}
      </div>

      <footer className="text-center text-gray-500 py-8 text-sm">
        ⚡ Сбор расписания раз в 3 часа • GitHub Actions
      </footer>
    </div>
  )
}

function ScheduleCard({ item }) {
  const [playing, setPlaying] = useState(false)

  return (
    <div className="bg-zinc-900 rounded-xl overflow-hidden shadow-lg hover:shadow-blue-900/20 transition-shadow">
      <div className="flex items-start p-4 gap-4">
        <img
          src={item.logo}
          alt={item.channel}
          className="w-16 h-16 rounded-lg object-cover shadow-md"
          onError={(e) => {
            e.target.src = 'https://via.placeholder.com/64/2d2d2d/ffffff?text=' + item.channel[0];
          }}
        />
        <div className="flex-1">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-bold text-xl">{item.channel}</h3>
              <p className="text-gray-300 text-lg">{item.program}</p>
              <p className="text-sm text-gray-500 mt-1">
                {item.start} — {item.end}
              </p>
            </div>
            {item.is_live && (
              <span className="bg-red-600 text-white text-xs font-bold px-3 py-1 rounded-md animate-pulse">
                🔴 В ЭФИРЕ
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="px-4 pb-4">
        {!playing ? (
          <button
            onClick={() => setPlaying(true)}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 text-white font-bold py-3 px-4 rounded-lg transition-transform active:scale-95 shadow-lg"
          >
            ▶ Смотреть сейчас
          </button>
        ) : (
          <div className="w-full h-64 bg-black rounded-lg overflow-hidden relative">
            <iframe
              src={`https://s1player.tatnet.app/?src=${encodeURIComponent(item.stream_url)}`}
              className="w-full h-full"
              allow="autoplay; encrypted-media"
              title={item.channel}
              frameBorder="0"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default App

const CityWiseAnalyse = ({ onBack }) => {
  return (
    <div className="rounded-xl bg-white/72 p-2 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="text-lg font-bold uppercase text-slate-900">
          City Wise Analyse
        </h3>
        <button
          type="button"
          onClick={onBack}
          className="rounded-md bg-cyan-600 px-3 py-1 text-sm font-semibold text-white transition hover:bg-cyan-700">
          Click
        </button>
      </div>
    </div>
  )
}

export default CityWiseAnalyse

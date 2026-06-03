import { useState } from 'react'
import { ChevronDownIcon } from './Icons'

const CityWiseAnalyse = ({ onBack }) => {
  const dropdownItems = [
    'Select city',
    'Delhi',
  ]
  const [selectedItem, setSelectedItem] = useState(dropdownItems[0])

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

      <div className="mt-4">
        {/* <label
          htmlFor="city-wise-item"
          className="mb-2 block text-xs font-semibold uppercase text-slate-500"
        >
          Select City
        </label> */}
        <div className="relative">
          <select
            id="city-wise-item"
            value={selectedItem}
            onChange={(event) => setSelectedItem(event.target.value)}
            className="w-full appearance-none rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 pr-10 text-sm font-semibold text-slate-800 shadow-sm outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-200"
          >
            {dropdownItems.map((item, index) => (
              <option
                key={item}
                value={item}
                disabled={index === 0}
              >
                {item}
              </option>
            ))}
          </select>
          <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-cyan-700" />
        </div>
      </div>
    </div>
  )
}

export default CityWiseAnalyse

import { useEffect, useState } from 'react'
import { ChevronDownIcon, SearchIcon, SparklesIcon } from './Icons'
import { fetchCityWiseDropdownItems } from '../services/api'
import targetIcon from '../assets/target.png'

const CityWiseAnalyse = ({ onBack }) => {
  const dropdownItems = [
    'Select city',
    'Delhi',
  ]
  const [selectedItem, setSelectedItem] = useState(dropdownItems[0])
  const [secondDropdownItems, setSecondDropdownItems] = useState([])
  const [selectedSecondItem, setSelectedSecondItem] = useState('')
  const [isLoadingItems, setIsLoadingItems] = useState(false)
  const [itemsError, setItemsError] = useState('')


  useEffect(() => {
    if (selectedItem === dropdownItems[0]) {
      setSecondDropdownItems([])
      setSelectedSecondItem('')
      setItemsError('')
      return
    }

    let ignore = false

    async function loadSecondDropdownItems() {
      setIsLoadingItems(true)
      setItemsError('')
      setSelectedSecondItem('')

      try {
        const items = await fetchCityWiseDropdownItems(selectedItem)
        if (!ignore) {
          setSecondDropdownItems(items)
        }
      } catch (error) {
        if (!ignore) {
          setSecondDropdownItems([])
          setItemsError('Unable to load items')
        }
      } finally {
        if (!ignore) {
          setIsLoadingItems(false)
        }
      }
    }

    loadSecondDropdownItems()

    return () => {
      ignore = true
    }
  }, [selectedItem])

  return (
    <div className="rounded-xl bg-white/72 p-2 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="text-lg font-bold uppercase text-slate-900">
          City Wise Analyse
        </h3>
        <div className="group relative inline-block">
          <button
            type="button"
            onClick={onBack}
            className="rounded-full bg-cyan-300 p-1 text-sm font-semibold text-white transition hover:bg-cyan-700">
            <img src={targetIcon} alt="Back" className="h-6 w-6" />
          </button>
          <span
            className="pointer-events-none absolute top-4 right-2 mt-3 rounded
                      bg-gray-800 px-2 py-1 text-xs text-white whitespace-nowrap
                      scale-95 opacity-0 transition-all duration-150
                      group-hover:scale-100 group-hover:opacity-100">
            Explore by location
          </span>
        </div>
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

      <div className="mt-3">
        <div className="relative ">
          <select
            id="city-wise-backend-item"
            value={selectedSecondItem}
            onChange={(event) => setSelectedSecondItem(event.target.value)}
            disabled={selectedItem === dropdownItems[0] || isLoadingItems || secondDropdownItems.length === 0}
            className="w-full appearance-none rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 pr-10 text-sm font-semibold text-slate-800 shadow-sm outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-200 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
          >
            <option value="">
              {isLoadingItems ? 'Loading items...' : secondDropdownItems.length ? 'Select item' : 'No items found'}
            </option>
            {secondDropdownItems.map((item) => {
              const value = typeof item === 'string'
                ? item
                : item.value || item.key || item.id || item.zone_id || item.zone || item.label || item.name
              const label = typeof item === 'string'
                ? item
                : item.label || item.name || item.zone_name || item.zone || item.value || item.key || item.id

              return (
                <option key={String(value)} value={value}>
                  {String(label)}
                </option>
              )
            })}
          </select>
          <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-cyan-700" />
        </div>
        <div className="mt-3">
          <button
            onClick={() => {
              onAnalyze()
            }}

            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/40 transition-all duration-200 hover:shadow-xl hover:shadow-blue-600/50  disabled:cursor-not-allowed disabled:from-[#87aacf] disabled:to-[#3d88d8] disabled:shadow-none disabled:opacity-60"
          >  <SparklesIcon className="h-5 w-5" />
            <span>
              Analyze Selected Zones
            </span>
          </button>

        </div>
        {itemsError && (
          <p className="mt-2 text-xs font-semibold text-rose-600">
            {itemsError}
          </p>
        )}
      </div>
    </div>
  )
}

export default CityWiseAnalyse

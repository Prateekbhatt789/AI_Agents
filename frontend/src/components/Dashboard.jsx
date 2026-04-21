import {
    BuildingIcon,
    BusIcon,
    ChartIcon,
    DownloadIcon,
    FuelIcon,
    HospitalIcon,
    PawIcon,
    PillIcon,
    PinIcon,
    SchoolIcon,
    UtensilsIcon
} from './Icons'
import { useState } from 'react';

export default function Dashboard({ locationName, summary, onDownload, onItemClick }) {
    const [selectedCategories, setSelectedCategories] = useState([]);
    const categories = [
        { key: 'human_hospitals', icon: HospitalIcon, label: 'Human Hospitals' },
        { key: 'vet_hospitals', icon: PawIcon, label: 'Veterinary Hospitals' },
        { key: 'bus_stops', icon: BusIcon, label: 'Bus Stops' },
        { key: 'fuel_stations', icon: FuelIcon, label: 'Fuel Stations' },
        { key: 'schools', icon: SchoolIcon, label: 'Schools' },
        { key: 'restaurants', icon: UtensilsIcon, label: 'Restaurants' },
        { key: 'pharmacies', icon: PillIcon, label: 'Pharmacies' },
        { key: 'buildings', icon: BuildingIcon, label: 'Buildings' },
    ]
    const toggleCategory = (key) => {
        setSelectedCategories((prev) =>
            prev.includes(key)
                ? prev.filter((k) => k !== key)
                : [...prev, key]
        );

        onItemClick?.(key)
    };
    return (
        <>
            <div className="rounded-xl border border-white/55 bg-white/72 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
                <div className="mb-3 flex items-center gap-3">
                    <div className="flex h-3 w-3 min-h-[2rem] min-w-[2rem] items-center justify-center rounded-full bg-slate-900 text-white shadow-lg shadow-slate-900/15">
                        <ChartIcon className="h-7 w-7" />
                    </div>
                    <div>
                        <h3 className="text-2xl font-bold uppercase  text-slate-900">
                            Dashboard
                        </h3>

                    </div>
                </div>

                {/* {locationName && (
                    <div className="mb-4 flex items-center gap-2 rounded-2xl border border-slate-200/80 bg-white/85 px-3 py-2 text-xs text-slate-600">
                        <PinIcon className="h-4 w-4 text-cyan-600" />
                        <p className="truncate">{locationName}</p>
                    </div>
                )} */}

                <div className="mb-2 grid grid-cols-1 gap-2">
                    {categories.map(({ key, icon: Icon, label }) => {
                        const isSelected = selectedCategories.includes(key);

                        return (
                            <div
                                key={key}
                                onClick={() => toggleCategory(key)}
                                className={`group flex items-center gap-1 rounded-full border px-2 py-2 shadow-sm transition-all duration-200 cursor-pointer
                ${isSelected
                                        ? "bg-[#14b8a6] text-white border-[#ffffff]"
                                        : "bg-[#f9f8f6] text-slate-700 border-slate-200 hover:bg-blue-50/50"
                                    }
                `}
                            >
                                {/* Icon + Label */}
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <span
                                        className={`flex h-6 w-6 items-center justify-center rounded-lg transition-transform duration-200 group-hover:scale-110
                        ${isSelected
                                                ? "bg-white/20 text-white"
                                                : "bg-gradient-to-br from-blue-100 to-cyan-100 text-[#64ae09]]"
                                            }
                        `}
                                    >
                                        <Icon className="h-5 w-5" />
                                    </span>

                                    <span
                                        className={`text-sm font-medium uppercase tracking-wide
                        ${isSelected ? "text-white" : "text-slate-500"}
                        `}
                                    >
                                        {label}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </>
    )
}

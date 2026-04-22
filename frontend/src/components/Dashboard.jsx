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
import { useState, useEffect } from 'react';
import { fetchDashboardCategories } from '../services/api';

export default function Dashboard({ locationName, summary, onDownload, onItemClick, onSelectionChange }) {
    const [selectedCategories, setSelectedCategories] = useState([]);
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        fetchDashboardCategories()
            .then(data => setCategories(data))
            .catch(err => setStatus('Error loading categories'));
    }, []);
    const toggleCategory = (key) => {
        const nextSelectedCategories = selectedCategories.includes(key)
            ? selectedCategories.filter((k) => k !== key)
            : [...selectedCategories, key];

        setSelectedCategories(nextSelectedCategories);
        onSelectionChange?.(nextSelectedCategories);
        onItemClick?.(nextSelectedCategories);
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
                    {categories.map(({ key, icon, label }) => { // 1. Removed 'icon: Icon' alias
                        const isSelected = selectedCategories.includes(key);

                        return (
                            <div
                                key={key}
                                onClick={() => toggleCategory(key)}
                                className={`group flex items-center gap-1 rounded-full border px-1 py-1 shadow-sm transition-all duration-200 cursor-pointer
                                ${isSelected
                                        ? "bg-[#14b8a6] text-white border-[#ffffff]"
                                        : "bg-[#f9f8f6] text-slate-700 border-slate-200 hover:bg-blue-50/100"
                                    }`}
                            >
                                <div className="flex items-center gap-4 flex-shrink-0">

                                    <span
                                        className={`flex h-8 w-8 items-center justify-center rounded-full overflow-hidden transition-transform duration-200 group-hover:scale-110 flex-shrink-0
                                                ${isSelected ? "bg-white/20" : "bg-blue-50"}
                                        `}
                                    >
                                        <div
                                            className="h-full w-full flex items-center justify-center"
                                            dangerouslySetInnerHTML={{ __html: icon }}
                                        />
                                    </span>

                                    <span
                                        className={`text-sm font-lg uppercase tracking-wide
              ${isSelected ? "text-white" : "text-slate-500"}`}
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

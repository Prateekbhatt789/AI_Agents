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

export default function Dashboard({ locationName, summary, onDownload }) {

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

    return (
        <div className="rounded-3xl border border-white/55 bg-white/72 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
            <div className="mb-3 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/15">
                    <ChartIcon className="h-5 w-5" />
                </div>
                <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-900">
                        Dashboard
                    </h3>
                    <p className="text-xs text-slate-500">
                        Live counts for the selected catchment.
                    </p>
                </div>
            </div>

            {locationName && (
                <div className="mb-4 flex items-center gap-2 rounded-2xl border border-slate-200/80 bg-white/85 px-3 py-2 text-xs text-slate-600">
                    <PinIcon className="h-4 w-4 text-cyan-600" />
                    <p className="truncate">{locationName}</p>
                </div>
            )}

            <div className="mb-4 grid grid-cols-3 gap-2">
                {categories.map(({ key, icon: Icon, label }) => (
                    <div
                        key={key}
                        className="flex flex-col items-center gap-2 rounded-2xl border border-slate-200/80 bg-gradient-to-b from-white to-slate-50 px-2 py-3 text-center shadow-sm"
                    >
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                            <Icon className="h-5 w-5" />
                        </span>
                        <span className="text-base font-bold text-slate-900">
                            {summary[key] ?? '-'}
                        </span>
                        <span className="text-[10px] text-slate-500">
                            {label}
                        </span>
                    </div>
                ))}
            </div>

            <button
                onClick={onDownload}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
                <DownloadIcon className="h-4 w-4" />
                Download PDF Report
            </button>
        </div>
    )
}

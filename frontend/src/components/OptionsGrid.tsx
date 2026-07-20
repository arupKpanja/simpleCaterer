import OptionCard from "./OptionCard";
import type { Option } from "../types";

export default function OptionsGrid({
  options,
  onSelect,
  selectingTier,
}: {
  options: Option[];
  onSelect?: (o: Option) => void;
  selectingTier?: string | null;
}) {
  if (!options.length) return null;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {options.map((o) => (
        <OptionCard
          key={o.tier}
          option={o}
          recommended={o.tier === "standard"}
          onSelect={onSelect}
          selecting={selectingTier === o.tier}
        />
      ))}
    </div>
  );
}

import { TrainFront, Plane, Droplets, Zap, Building2 } from "lucide-react";

export function SectorIcon({ name, size = 18, ...rest }) {
  const C =
    {
      Railways: TrainFront,
      "Water Resources": Droplets,
      "Aviation & Aviation Infrastructure": Plane,
      Power: Zap,
    }[name] || Building2;
  return <C size={size} {...rest} />;
}

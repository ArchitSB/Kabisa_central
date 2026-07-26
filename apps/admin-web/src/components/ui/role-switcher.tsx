import { ChevronDown, FlaskConical } from "lucide-react";

type RoleSwitcherProps = {
  role: string;
  onRoleChange: (role: string) => void;
};

const roles = ["Super admin", "Manager", "Sales", "Inventory", "Accounts"];

export function RoleSwitcher({ role, onRoleChange }: RoleSwitcherProps) {
  return (
    <div className="relative hidden items-center md:flex">
      <FlaskConical
        aria-hidden="true"
        className="pointer-events-none absolute left-3 size-3.5 text-primary-700"
      />
      <select
        aria-label="Dev viewing role"
        value={role}
        onChange={(event) => onRoleChange(event.target.value)}
        className="h-10 appearance-none rounded-full border border-primary-200 bg-primary-50 pl-9 pr-9 text-xs font-semibold text-primary-900 transition-colors duration-standard hover:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-500/15"
      >
        {roles.map((item) => (
          <option key={item} value={item}>
            Dev · Viewing as {item}
          </option>
        ))}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-3 size-3.5 text-primary-700"
      />
    </div>
  );
}

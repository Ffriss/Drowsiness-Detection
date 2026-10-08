"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Eye, LayoutDashboard, BarChart3, History, Cpu } from "lucide-react";

const ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/compare", label: "เปรียบเทียบโมเดล", icon: BarChart3 },
  { href: "/models/custom_cnn", label: "CNN", icon: Cpu, group: "models" },
  { href: "/models/mobilenetv2", label: "MobileNetV2", icon: Cpu, group: "models" },
  { href: "/models/resnet50", label: "ResNet50", icon: Cpu, group: "models" },
  { href: "/history", label: "ประวัติ", icon: History },
];

export default function Nav() {
  const path = usePathname();
  const active = (href) => (href === "/" ? path === "/" : path.startsWith(href));
  return (
    <nav className="border-b border-navy-700 bg-navy-900 md:min-h-screen md:w-60 md:shrink-0 md:border-b-0 md:border-r">
      <div className="flex items-center gap-2 px-5 py-4 md:py-6">
        <Eye className="h-6 w-6 text-accent" aria-hidden />
        <span className="text-base font-semibold leading-tight">ตรวจจับการหลับในและการละสายตา</span>
      </div>
      <ul className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-0">
        {ITEMS.map(({ href, label, icon: Icon, group }) => (
          <li key={href} className={group ? "md:ml-4" : ""}>
            <Link
              href={href}
              aria-current={active(href) ? "page" : undefined}
              className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors ${
                active(href) ? "bg-navy-700 text-ink" : "text-mute hover:bg-navy-800 hover:text-ink"
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

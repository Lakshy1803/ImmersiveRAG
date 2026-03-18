import Image from "next/image";
import ThemeToggle from "./ThemeToggle";

const Header: React.FC = () => {
  return (
    <header className="fixed top-0 w-full z-50 bg-surface-container/80 backdrop-blur-md flex justify-between items-center px-8 h-16 border-b border-outline-variant/30">
      <div className="flex items-center gap-4">
        <Image
          src="/PwC_Company_Logo.svg"
          alt="PwC Logo"
          width={180}
          height={90}
          className="h-8 w-auto text-on-surface transition-all duration-300 select-none object-contain"
        />
      </div>
      <div className="flex items-center gap-4">
        <ThemeToggle />
      </div>
    </header>
  );
};

export default Header;

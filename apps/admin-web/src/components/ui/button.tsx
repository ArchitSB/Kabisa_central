import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded-control px-4 text-sm font-semibold transition-colors duration-standard ease-kabisa focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary-500/20 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-primary-700 text-white shadow-sm hover:bg-primary-800 active:bg-primary-900",
        secondary:
          "border border-border bg-surface text-foreground shadow-sm hover:border-primary-200 hover:bg-primary-50",
        outline:
          "border border-primary-200 bg-surface text-primary-800 hover:border-primary-400 hover:bg-primary-50",
        ghost: "text-secondary hover:bg-primary-50 hover:text-primary-800",
        destructive: "text-danger hover:bg-danger-surface",
      },
      size: {
        default: "h-10",
        sm: "h-8 min-h-8 rounded-full px-3 text-xs",
        lg: "h-11 px-5",
        icon: "size-10 min-h-10 px-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button };

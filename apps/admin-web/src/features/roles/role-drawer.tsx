import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Input } from "@/components/ui/input";
import type { Permission, RoleWithPermissions } from "@/features/auth/types";
import { createRole, listPermissions, updateRole } from "@/features/roles/roles-api";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatRoleName } from "@/lib/utils";

const roleSchema = z.object({
  name: z
    .string()
    .trim()
    .min(3, "Use at least 3 characters.")
    .max(50)
    .regex(
      /^[a-z][a-z0-9_]*$/,
      "Use lowercase letters, numbers, and underscores; start with a letter.",
    ),
  description: z.string().trim().min(1, "Describe what this role is for.").max(500),
  permissionCodes: z.array(z.string()),
});

type RoleValues = z.infer<typeof roleSchema>;

type RoleDrawerProps = {
  trigger: React.ReactNode;
  role?: RoleWithPermissions;
};

export function RoleDrawer({ trigger, role }: RoleDrawerProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const editing = Boolean(role);
  const permissionsQuery = useQuery({
    queryKey: ["permissions"],
    queryFn: listPermissions,
    enabled: open,
    staleTime: 5 * 60 * 1000,
  });
  const {
    handleSubmit,
    register,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<RoleValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: {
      name: "",
      description: "",
      permissionCodes: [],
    },
  });
  const selectedCodes = watch("permissionCodes");
  const groupedPermissions = useMemo(
    () => groupPermissions(permissionsQuery.data?.items ?? []),
    [permissionsQuery.data?.items],
  );
  const mutation = useMutation({
    mutationFn: (values: RoleValues) => {
      const payload = {
        name: values.name,
        description: values.description,
        permission_codes: values.permissionCodes,
      };
      return role ? updateRole(role.id, payload) : createRole(payload);
    },
    onSuccess: async (savedRole) => {
      await queryClient.invalidateQueries({ queryKey: ["roles"] });
      toast.success(editing ? "Role updated" : "Role created", {
        description: `${formatRoleName(savedRole.name)} now has ${savedRole.permissions.length} permissions.`,
      });
      setOpen(false);
    },
    onError: (error) => {
      toast.error(editing ? "Could not update role" : "Could not create role", {
        description: getApiErrorDetail(error),
      });
    },
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    reset({
      name: role?.name ?? "",
      description: role?.description ?? "",
      permissionCodes: role?.permissions.map((permission) => permission.code) ?? [],
    });
  }, [open, reset, role]);

  function togglePermission(code: string, checked: boolean) {
    setValue(
      "permissionCodes",
      checked
        ? Array.from(new Set([...selectedCodes, code]))
        : selectedCodes.filter((selectedCode) => selectedCode !== code),
      { shouldDirty: true },
    );
  }

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent className="max-w-[660px]">
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Permission design
          </p>
          <DrawerTitle>{editing ? "Edit custom role" : "Create custom role"}</DrawerTitle>
          <DrawerDescription>
            Give the role a stable code and select only the permissions its members need.
          </DrawerDescription>
        </DrawerHeader>

        <form
          className="flex flex-1 flex-col"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <div>
              <label htmlFor="role-name" className="mb-2 block text-sm font-semibold">
                Role code
              </label>
              <Input
                id="role-name"
                autoComplete="off"
                placeholder="regional_manager"
                aria-invalid={Boolean(errors.name)}
                {...register("name")}
              />
              {errors.name ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.name.message}
                </p>
              ) : (
                <p className="mt-1.5 text-xs text-secondary">
                  Lowercase letters, numbers, and underscores only.
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="role-description"
                className="mb-2 block text-sm font-semibold"
              >
                Description
              </label>
              <textarea
                id="role-description"
                rows={3}
                className="control-base h-auto w-full resize-y py-3"
                aria-invalid={Boolean(errors.description)}
                {...register("description")}
              />
              {errors.description ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.description.message}
                </p>
              ) : null}
            </div>

            <fieldset>
              <div className="flex items-center justify-between gap-3">
                <legend className="text-sm font-semibold">Permissions</legend>
                <span className="numeric text-xs font-semibold text-secondary">
                  {selectedCodes.length} selected
                </span>
              </div>
              {permissionsQuery.isPending ? (
                <div className="mt-3 flex min-h-32 items-center justify-center rounded-card border border-border">
                  <LoaderCircle
                    aria-hidden="true"
                    className="size-5 animate-spin text-primary-700"
                  />
                  <span className="ml-2 text-sm text-secondary">Loading permissions…</span>
                </div>
              ) : (
                <div className="mt-3 space-y-3">
                  {Object.entries(groupedPermissions).map(([group, permissions]) => (
                    <div key={group} className="rounded-card border border-border p-4">
                      <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.1em] text-primary-700">
                        {group}
                      </p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {permissions.map((permission) => (
                          <label
                            key={permission.id}
                            className="flex items-start gap-3 rounded-control p-1"
                          >
                            <Checkbox
                              checked={selectedCodes.includes(permission.code)}
                              onCheckedChange={(value) =>
                                togglePermission(permission.code, Boolean(value))
                              }
                              aria-label={`Grant ${permission.code}`}
                            />
                            <span className="min-w-0">
                              <span className="block break-all font-mono text-[11px] font-semibold text-foreground">
                                {permission.code}
                              </span>
                              <span className="mt-0.5 block text-xs leading-5 text-secondary">
                                {permission.description}
                              </span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </fieldset>
          </div>

          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button
              type="submit"
              disabled={mutation.isPending || permissionsQuery.isPending}
            >
              {mutation.isPending ? (
                <>
                  <LoaderCircle aria-hidden="true" className="animate-spin" />
                  Saving…
                </>
              ) : editing ? (
                "Save role"
              ) : (
                "Create role"
              )}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}

function groupPermissions(permissions: Permission[]): Record<string, Permission[]> {
  return permissions.reduce<Record<string, Permission[]>>((groups, permission) => {
    (groups[permission.group] ??= []).push(permission);
    return groups;
  }, {});
}

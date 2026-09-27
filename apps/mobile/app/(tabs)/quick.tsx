import { useState } from "react";
import { Pressable, View } from "react-native";
import { router } from "expo-router";
import type { Page, Product } from "@kabisa/api-client";
import { parseQuickOrder } from "@kabisa/core";
import { api } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  Badge,
  Empty,
  Input,
  Panel,
  Quantity,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
type Match = {
  text: string;
  quantity: number;
  choices: Product[];
  selected: string;
  error?: string;
};
export default function Quick() {
  const { authenticated, add, refresh } = useStore();
  const [input, setInput] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);
  async function match() {
    const parsed = parseQuickOrder(input);
    const result: Match[] = [];
    for (let start = 0; start < parsed.length; start += 5) {
      result.push(
        ...(await Promise.all(
          parsed.slice(start, start + 5).map(async (line) => {
            if (line.error)
              return {
                text: line.query,
                quantity: line.quantity,
                choices: [],
                selected: "",
                error: line.error,
              };
            const data = await api.get<Page<Product>>(
              "/catalog/products?search=" +
                encodeURIComponent(line.query) +
                "&page_size=8",
            );
            const exact = data.items.find(
              (p) =>
                p.sku.toLowerCase() === line.query.toLowerCase() ||
                p.name.toLowerCase() === line.query.toLowerCase(),
            );
            return {
              text: line.query,
              quantity: line.quantity,
              choices: data.items,
              selected:
                exact?.id || (data.items.length === 1 ? data.items[0].id : ""),
            };
          }),
        )),
      );
    }
    setMatches(result);
  }
  const selected = matches.filter((m) => m.selected && !m.error);
  return (
    <Screen
      title={t("quick.title")}
      eyebrow={t("nav.quick")}
      body={t("quick.subtitle")}
    >
      <Panel>
        <Input
          label={t("quick.label")}
          multiline
          value={input}
          onChangeText={setInput}
          placeholder={t("quick.placeholder")}
        />
        <Txt muted small>
          {t("quick.hint")}
        </Txt>
        <Action
          label={t("quick.match")}
          onPress={match}
          disabled={!input.trim()}
        />
      </Panel>
      {!matches.length ? (
        <Empty title={t("quick.empty")} body={t("quick.emptyBody")} />
      ) : (
        <>
          <Txt>{t("quick.review")}</Txt>
          {matches.map((m, index) => (
            <Panel key={index}>
              <Txt>{m.text}</Txt>
              {m.error ? (
                <Txt>{t("quick.invalid")}</Txt>
              ) : !m.choices.length ? (
                <Txt>{t("quick.noMatch")}</Txt>
              ) : (
                <>
                  {m.choices.map((p) => (
                    <Pressable
                      style={[s.chip, m.selected === p.id && s.chipActive]}
                      key={p.id}
                      onPress={() =>
                        setMatches((old) =>
                          old.map((item, i) =>
                            i === index ? { ...item, selected: p.id } : item,
                          ),
                        )
                      }
                    >
                      <Txt>{p.name}</Txt>
                      <View style={s.between}>
                        <Txt small muted>
                          {p.sku}
                        </Txt>
                        <Badge status={p.availability} />
                      </View>
                    </Pressable>
                  ))}
                  <Quantity
                    value={m.quantity}
                    onChange={(quantity) =>
                      setMatches((old) =>
                        old.map((item, i) =>
                          i === index ? { ...item, quantity } : item,
                        ),
                      )
                    }
                  />
                </>
              )}
            </Panel>
          ))}
          <Action
            label={`${t("quick.addAll")} (${selected.length})`}
            disabled={!selected.length}
            onPress={async () => {
              if (authenticated)
                await api.post("/cart/merge", {
                  items: selected.map((m) => ({
                    product_id: m.selected,
                    quantity: m.quantity,
                  })),
                });
              else
                for (const m of selected)
                  await add(
                    m.choices.find((p) => p.id === m.selected)!,
                    m.quantity,
                  );
              await refresh();
              router.push("/cart");
            }}
          />
        </>
      )}
    </Screen>
  );
}

from socrata_toolkit import SocrataClient, SoQLBuilder


def main():
    # 1. Initialize the client
    client = SocrataClient()

    # 2. Build a sophisticated SoQL query using the fluent builder
    # Reference: https://dev.socrata.com/docs/functions/
    query = (
        SoQLBuilder()
        .select("incident_address", "borough", "created_date", "descriptor")
        .where("borough = 'MANHATTAN'")
        .where(SoQLBuilder.between("created_date", "2024-01-01", "2024-03-01"))
        .order("created_date", desc=True)
        .limit(10)
    )

    print("Generated SoQL Query Parameters:")
    print(query.build())

    print("\nRaw SoQL String:")
    print(query.build_query_string())

    # 3. Execute the query
    # Example dataset: NYC 311 Service Requests (erm2-nwe9)
    try:
        df = client.fetch_dataframe(
            domain="data.cityofnewyork.us", fourfour="erm2-nwe9", **query.build()
        )

        print(f"\nSuccessfully fetched {len(df)} rows.")
        print(df.head())

    except Exception as e:
        print(f"\nError fetching data: {e}")


if __name__ == "__main__":
    main()

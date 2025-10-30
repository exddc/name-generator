// Libraries
import React from 'react';
import { cn } from '@/lib/utils';

// Components
import HeroBackground from '@/components/HeroBackground';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function Home() {
    return (
        <main className="flex flex-col items-center justify-center max-w-6xl gap-64 mx-auto px-6 xl:px-0">
            <HeroBackground />

            <Card className="max-w-2xl h-96 -mt-64 gap-4 flex-col">
                <div className="w-full max-w-2xl flex flex-row items-center justify-center gap-4">
                    <Button>Primary</Button>
                    <Button variant="outline">Outline</Button>
                    <Button variant="outline" size="sm">
                        Outline Small
                    </Button>
                </div>
                <Card className="h-64">
                    <div className="w-full max-w-2xl flex flex-row items-center justify-center gap-4">
                        <Button>Primary</Button>
                        <Button variant="outline">Outline</Button>
                        <Button variant="outline" size="sm">
                            Outline Small
                        </Button>
                    </div>
                </Card>
            </Card>
        </main>
    );
}
